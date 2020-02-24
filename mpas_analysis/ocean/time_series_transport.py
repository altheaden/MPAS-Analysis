# This software is open source software available under the BSD-3 license.
#
# Copyright (c) 2020 Triad National Security, LLC. All rights reserved.
# Copyright (c) 2020 Lawrence Livermore National Security, LLC. All rights
# reserved.
# Copyright (c) 2020 UT-Battelle, LLC. All rights reserved.
#
# Additional copyright and license information can be found in the LICENSE file
# distributed with this code, or at
# https://raw.githubusercontent.com/MPAS-Dev/MPAS-Analysis/master/LICENSE
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import os
import xarray
import numpy
import dask
import multiprocessing
from multiprocessing.pool import ThreadPool
import matplotlib.pyplot as plt

from geometric_features import FeatureCollection, read_feature_collection

from mpas_analysis.shared.analysis_task import AnalysisTask

from mpas_analysis.shared.constants import constants

from mpas_analysis.shared.plot import timeseries_analysis_plot, savefig, \
    add_inset

from mpas_analysis.shared.io import open_mpas_dataset, write_netcdf

from mpas_analysis.shared.io.utility import build_config_full_path, \
    get_files_year_month, decode_strings, get_region_mask

from mpas_analysis.shared.html import write_image_xml

from mpas_analysis.shared.transects import ComputeTransectMasksSubtask

from mpas_analysis.shared.regions import get_feature_list


class TimeSeriesTransport(AnalysisTask):  # {{{
    """
    Extract and plot time series of transport through transects on the MPAS
    mesh.
    """
    # Authors
    # -------
    # Xylar Asay-Davis, Stephen Price

    def __init__(self, config, controlConfig=None):
        # {{{
        """
        Construct the analysis task.

        Parameters
        ----------
        config :  ``MpasAnalysisConfigParser``
            Configuration options

        controlConfig :  ``MpasAnalysisConfigParser``, optional
            Configuration options for a control run (if any)
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # first, call the constructor from the base class (AnalysisTask)
        super(TimeSeriesTransport, self).__init__(
            config=config,
            taskName='timeSeriesTransport',
            componentName='ocean',
            tags=['timeSeries', 'transport'])

        startYear = config.getint('timeSeries', 'startYear')
        endYear = config.getint('timeSeries', 'endYear')

        years = [year for year in range(startYear, endYear + 1)]

        transportTransectFileName = \
            get_region_mask(config, 'transportTransects.geojson')

        transectsToPlot = config.getExpression('timeSeriesTransport',
                                               'transectsToPlot')
        if 'all' in transectsToPlot:
            transectsToPlot = get_feature_list(transportTransectFileName)

        masksSubtask = ComputeTransectMasksSubtask(
            self, transportTransectFileName, outFileSuffix='transportMasks')

        self.add_subtask(masksSubtask)

        # in the end, we'll combine all the time series into one, but we
        # create this task first so it's easier to tell it to run after all
        # the compute tasks
        combineSubtask = CombineTransportSubtask(
            self, startYears=years, endYears=years)

        # run one subtask per year
        for year in years:
            computeSubtask = ComputeTransportSubtask(
                self, startYear=year, endYear=year, masksSubtask=masksSubtask,
                transectsToPlot=transectsToPlot)
            self.add_subtask(computeSubtask)
            computeSubtask.run_after(masksSubtask)
            combineSubtask.run_after(computeSubtask)

        for index, transect in enumerate(transectsToPlot):
            plotTransportSubtask = PlotTransportSubtask(
                self, transect, index, controlConfig, transportTransectFileName)
            plotTransportSubtask.run_after(combineSubtask)
            self.add_subtask(plotTransportSubtask)

        # }}}

    # }}}


class ComputeTransportSubtask(AnalysisTask):  # {{{
    """
    Computes time-series of transport through transects.

    Attributes
    ----------
    startYear, endYear : int
        The beginning and end of the time series to compute

    masksSubtask : ``ComputeRegionMasksSubtask``
        A task for creating mask files for each ice shelf to plot

    transectsToPlot : list of str
        A list of transects to plot
    """
    # Authors
    # -------
    # Xylar Asay-Davis, Stephen Price

    def __init__(self, parentTask, startYear, endYear,
                 masksSubtask, transectsToPlot):  # {{{
        """
        Construct the analysis task.

        Parameters
        ----------
        parentTask :  ``AnalysisTask``
            The parent task, used to get the ``taskName``, ``config`` and
            ``componentName``

        startYear, endYear : int
            The beginning and end of the time series to compute

        masksSubtask : ``ComputeRegionMasksSubtask``
            A task for creating mask files for each ice shelf to plot

        transectsToPlot : list of str
            A list of transects to plot
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # first, call the constructor from the base class (AnalysisTask)
        super(ComputeTransportSubtask, self).__init__(
            config=parentTask.config,
            taskName=parentTask.taskName,
            componentName=parentTask.componentName,
            tags=parentTask.tags,
            subtaskName='computeTransport_{:04d}-{:04d}'.format(startYear,
                                                                endYear))

        self.startYear = startYear
        self.endYear = endYear

        self.masksSubtask = masksSubtask
        self.run_after(masksSubtask)

        self.transectsToPlot = transectsToPlot

        parallelTaskCount = self.config.getint('execute', 'parallelTaskCount')
        self.subprocessCount = min(parallelTaskCount,
                                   self.config.getint(self.taskName,
                                                      'subprocessCount'))
        self.daskThreads = min(
            multiprocessing.cpu_count(),
            self.config.getint(self.taskName, 'daskThreads'))

        self.restartFileName = None
        # }}}

    def setup_and_check(self):  # {{{
        """
        Perform steps to set up the analysis and check for errors in the setup.

        Raises
        ------
        IOError
            If a restart file is not present

        ValueError
            If ``config_land_ice_flux_mode`` is not one of ``standalone`` or
            ``coupled``
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # first, call setup_and_check from the base class (AnalysisTask),
        # which will perform some common setup, including storing:
        #   self.inDirectory, self.plotsDirectory, self.namelist, self.streams
        #   self.calendar
        super(ComputeTransportSubtask, self).setup_and_check()

        self.check_analysis_enabled(
            analysisOptionName='config_am_timeseriesstatsmonthly_enable',
            raiseException=True)

        # Load mesh related variables
        try:
            self.restartFileName = self.runStreams.readpath('restart')[0]
        except ValueError:
            raise IOError('No MPAS-O restart file found: need at least one '
                          'restart file for transport calculations')

        # }}}

    def run_task(self):  # {{{
        """
        Computes time-series of transport through transects.
        """
        # Authors
        # -------
        # Xylar Asay-Davis, Stephen Price

        self.logger.info("Computing time series of transport through "
                         "transects...")

        self.logger.info('  Load transport velocity data...')

        config = self.config

        startDate = '{:04d}-01-01_00:00:00'.format(self.startYear)
        endDate = '{:04d}-12-31_23:59:59'.format(self.endYear)

        outputDirectory = '{}/transport/'.format(
            build_config_full_path(config, 'output', 'timeseriesSubdirectory'))
        try:
            os.makedirs(outputDirectory)
        except OSError:
            pass

        outFileName = '{}/transport_{:04d}-{:04d}.nc'.format(
            outputDirectory, self.startYear, self.endYear)

        inputFiles = sorted(self.historyStreams.readpath(
            'timeSeriesStatsMonthlyOutput', startDate=startDate,
            endDate=endDate, calendar=self.calendar))

        years, months = get_files_year_month(inputFiles,
                                             self.historyStreams,
                                             'timeSeriesStatsMonthlyOutput')

        variableList = ['timeMonthly_avg_layerThickness']
        with open_mpas_dataset(fileName=inputFiles[0],
                               calendar=self.calendar,
                               startDate=startDate,
                               endDate=endDate) as dsIn:
            if 'timeMonthly_avg_normalTransportVelocity' in dsIn:
                variableList.append('timeMonthly_avg_normalTransportVelocity')
            elif 'timeMonthly_avg_normalGMBolusVelocity' in dsIn:
                variableList = variableList + \
                    ['timeMonthly_avg_normalVelocity',
                     'timeMonthly_avg_normalGMBolusVelocity']
            else:
                self.logger.warning('Cannot compute transport velocity. '
                                    'Using advection velocity.')
                variableList.append('timeMonthly_avg_normalVelocity')

        outputExists = os.path.exists(outFileName)
        outputValid = outputExists
        if outputExists:
            with open_mpas_dataset(fileName=outFileName,
                                   calendar=self.calendar,
                                   timeVariableNames=None,
                                   variableList=None,
                                   startDate=startDate,
                                   endDate=endDate) as dsOut:

                for inIndex in range(dsOut.dims['Time']):

                    mask = numpy.logical_and(
                        dsOut.year[inIndex].values == years,
                        dsOut.month[inIndex].values == months)
                    if numpy.count_nonzero(mask) == 0:
                        outputValid = False
                        break

        if outputValid:
            self.logger.info('  Time series exists -- Done.')
            return

        datasets = []
        for fileName in inputFiles:

            dsTimeSlice = open_mpas_dataset(
                fileName=fileName,
                calendar=self.calendar,
                variableList=variableList,
                startDate=startDate,
                endDate=endDate)
            datasets.append(dsTimeSlice)

        # Load data:
        dsIn = xarray.concat(datasets, 'Time').chunk({'Time': 1})

        with dask.config.set(schedular='threads',
                             pool=ThreadPool(self.daskThreads)):

            dsMesh = xarray.open_dataset(self.restartFileName)
            dvEdge = dsMesh.dvEdge

            # work on data from simulations
            if 'timeMonthly_avg_normalTransportVelocity' in dsIn:
                vel = dsIn.timeMonthly_avg_normalTransportVelocity
            elif 'timeMonthly_avg_normalGMBolusVelocity' in dsIn:
                vel = (dsIn.timeMonthly_avg_normalVelocity +
                       dsIn.timeMonthly_avg_normalGMBolusVelocity)
            else:
                vel = dsIn.timeMonthly_avg_normalVelocity

            # get layer thickness on edges by averaging adjacent cells
            h = 0.5*dsIn.timeMonthly_avg_layerThickness.isel(
                nCells=(dsMesh.cellsOnEdge-1)).sum(dim='TWO')

            transectMaskFileName = self.masksSubtask.maskFileName

            dsTransectMask = xarray.open_dataset(transectMaskFileName)

            # figure out the indices of the transects to plot
            transectNames = decode_strings(dsTransectMask.transectNames)

            transectIndices = []
            outTransectNames = []
            for transect in self.transectsToPlot:
                found = False
                for index, otherName in enumerate(transectNames):
                    if transect == otherName:
                        transectIndices.append(index)
                        outTransectNames.append(transect)
                        found = True
                        break
                if not found:
                    self.logger.warning('transect {} was not found in transect '
                                        'masks'.format(transect))

            # select only those transects we want to plot
            dsTransectMask = dsTransectMask.isel(nTransects=transectIndices)
            edgeSign = dsTransectMask.transectEdgeMaskSigns.chunk(
                {'nTransects': 5})

            # convert from m^3/s to Sv
            transport = (constants.m3ps_to_Sv *
                         (edgeSign * vel * h * dvEdge).sum(
                             dim=['nEdges', 'nVertLevels']))
            self.logger.info(transport)
            transport.compute()

            dsOut = xarray.Dataset()
            dsOut['transport'] = transport
            dsOut.transport.attrs['units'] = 'Sv'
            dsOut.transport.attrs['description'] = \
                'Transport through transects'
            dsOut.coords['transectNames'] = ('nTransects', outTransectNames)

            write_netcdf(dsOut, outFileName)

        # }}}

    # }}}


class CombineTransportSubtask(AnalysisTask):  # {{{
    """
    Combine individual time series into a single data set
    """
    # Authors
    # -------
    # Xylar Asay-Davis

    def __init__(self, parentTask, startYears, endYears):  # {{{
        """
        Construct the analysis task.

        Parameters
        ----------
        parentTask : ``TimeSeriesOceanRegions``
            The main task of which this is a subtask

        startYears, endYears : list of int
            The beginning and end of each time series to combine

        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # first, call the constructor from the base class (AnalysisTask)
        super(CombineTransportSubtask, self).__init__(
            config=parentTask.config,
            taskName=parentTask.taskName,
            componentName=parentTask.componentName,
            tags=parentTask.tags,
            subtaskName='combineTimeSeries')

        self.startYears = startYears
        self.endYears = endYears
        # }}}

    def run_task(self):  # {{{
        """
        Combine the time series
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        outputDirectory = '{}/transport/'.format(
            build_config_full_path(self.config, 'output',
                                   'timeseriesSubdirectory'))

        outFileName = '{}/transport_{:04d}-{:04d}.nc'.format(
            outputDirectory, self.startYears[0], self.endYears[-1])

        if not os.path.exists(outFileName):
            inFileNames = []
            for startYear, endYear in zip(self.startYears, self.endYears):
                inFileName = '{}/transport_{:04d}-{:04d}.nc'.format(
                    outputDirectory, startYear, endYear)
                inFileNames.append(inFileName)

            ds = xarray.open_mfdataset(inFileNames, combine='nested',
                                       concat_dim='Time', decode_times=False)

            write_netcdf(ds, outFileName)
        # }}}
    # }}}


class PlotTransportSubtask(AnalysisTask):
    """
    Plots time-series output of transport through transects.

    Attributes
    ----------
    transect : str
        Name of the transect to plot

    transectIndex : int
        The index into the dimension ``nTransects`` of the transect to plot

    controlConfig : ``MpasAnalysisConfigParser``
        The configuration options for the control run (if any)

    """
    # Authors
    # -------
    # Xylar Asay-Davis, Stephen Price

    def __init__(self, parentTask, transect, transectIndex, controlConfig,
                 transportTransectFileName):
        # {{{
        """
        Construct the analysis task.

        Parameters
        ----------
        parentTask :  ``AnalysisTask``
            The parent task, used to get the ``taskName``, ``config`` and
            ``componentName``

        transect : str
            Name of the transect to plot

        transectIndex : int
            The index into the dimension ``nTransects`` of the transect to plot

        controlConfig :  ``MpasAnalysisConfigParser``, optional
            Configuration options for a control run (if any)
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # first, call the constructor from the base class (AnalysisTask)
        super(PlotTransportSubtask, self).__init__(
            config=parentTask.config,
            taskName=parentTask.taskName,
            componentName=parentTask.componentName,
            tags=parentTask.tags,
            subtaskName='plotTransport_{}'.format(transect.replace(' ', '_')))

        self.transportTransectFileName = transportTransectFileName
        self.transect = transect
        self.transectIndex = transectIndex
        self.controlConfig = controlConfig

        # }}}

    def setup_and_check(self):  # {{{
        """
        Perform steps to set up the analysis and check for errors in the setup.

        Raises
        ------
        IOError
            If files are not present
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # first, call setup_and_check from the base class (AnalysisTask),
        # which will perform some common setup, including storing:
        #   self.inDirectory, self.plotsDirectory, self.namelist, self.streams
        #   self.calendar
        super(PlotTransportSubtask, self).setup_and_check()

        self.xmlFileNames = ['{}/transport_{}.xml'.format(
            self.plotsDirectory, self.transect.replace(' ', '_'))]
        # }}}

    def run_task(self):  # {{{
        """
        Plots time-series output of transport through transects.
        """
        # Authors
        # -------
        # Xylar Asay-Davis, Stephen Price

        self.logger.info("\nPlotting time series of transport through "
                         "{}...".format(self.transect))

        self.logger.info('  Load transport data...')

        config = self.config
        calendar = self.calendar

        fcAll = read_feature_collection(self.transportTransectFileName)

        fc = FeatureCollection()
        for feature in fcAll.features:
            if feature['properties']['name'] == self.transect:
                fc.add_feature(feature)
                break

        transport = self._load_transport(config)

        plotControl = self.controlConfig is not None

        mainRunName = config.get('runs', 'mainRunName')
        movingAverageMonths = config.getint('timeSeriesTransport',
                                            'movingAverageMonths')

        self.logger.info('  Plotting...')

        title = self.transect.replace('_', ' ')

        xLabel = 'Time (yr)'
        yLabel = 'Transport (Sv)'

        filePrefix = 'transport_{}'.format(self.transect.replace(' ', '_'))
        outFileName = '{}/{}.png'.format(self.plotsDirectory, filePrefix)

        fields = [transport]
        lineColors = ['k']
        lineWidths = [2.5]
        legendText = [mainRunName]
        if plotControl:
            controlRunName = self.controlConfig.get('runs', 'mainRunName')
            refTransport = self._load_transport(self.controlConfig)
            fields.append(refTransport)
            lineColors.append('r')
            lineWidths.append(1.2)
            legendText.append(controlRunName)

        if config.has_option(self.taskName, 'firstYearXTicks'):
            firstYearXTicks = config.getint(self.taskName,
                                            'firstYearXTicks')
        else:
            firstYearXTicks = None

        if config.has_option(self.taskName, 'yearStrideXTicks'):
            yearStrideXTicks = config.getint(self.taskName,
                                             'yearStrideXTicks')
        else:
            yearStrideXTicks = None

        fig = timeseries_analysis_plot(config, fields, movingAverageMonths,
                                       title, xLabel, yLabel,
                                       calendar=calendar,
                                       lineColors=lineColors,
                                       lineWidths=lineWidths,
                                       legendText=legendText,
                                       firstYearXTicks=firstYearXTicks,
                                       yearStrideXTicks=yearStrideXTicks)

        # do this before the inset because otherwise it moves the inset
        # and cartopy doesn't play too well with tight_layout anyway
        plt.tight_layout()

        add_inset(fig, fc, width=2.0, height=2.0)

        savefig(outFileName)

        caption = 'Transport through the {} Transect'.format(title)
        write_image_xml(
            config=config,
            filePrefix=filePrefix,
            componentName='Ocean',
            componentSubdirectory='ocean',
            galleryGroup='Transport Time Series',
            groupLink='transporttime',
            thumbnailDescription=title,
            imageDescription=caption,
            imageCaption=caption)
        # }}}

    def _load_transport(self, config):  # {{{
        """
        Reads transport time series for this transect
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        baseDirectory = build_config_full_path(
            config, 'output', 'timeSeriesSubdirectory')

        startYear = config.getint('timeSeries', 'startYear')
        endYear = config.getint('timeSeries', 'endYear')

        inFileName = '{}/transport/transport_{:04d}-{:04d}.nc'.format(
            baseDirectory, startYear, endYear)

        dsIn = xarray.open_dataset(inFileName)
        return dsIn.transport.isel(nTransects=self.transectIndex)  # }}}

    # }}}

# vim: foldmethod=marker ai ts=4 sts=4 et sw=4 ft=python
