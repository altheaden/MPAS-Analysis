# -*- coding: utf-8 -*-
#
# MPAS-Analysis documentation build configuration file, created by
# sphinx-quickstart on Sat Mar 25 14:39:11 2017.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os
import m2r2
from glob import glob
import mpas_analysis
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    os.environ['PROJ_LIB'] = '{}/{}/share/proj'.format(
            os.environ['CONDA_ENVS_PATH'], os.environ['CONDA_DEFAULT_ENV'])
else:
    os.environ['PROJ_LIB'] = '{}/share/proj'.format(os.environ['CONDA_PREFIX'])
from mpas_analysis.docs.parse_table import build_rst_table_from_xml, \
    build_obs_pages_from_xml
from mpas_analysis.docs.parse_quick_start import build_quick_start

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.autosummary',
              'sphinx.ext.intersphinx',
              'sphinx.ext.mathjax',
              'sphinx.ext.viewcode',
              'sphinx.ext.napoleon']

autosummary_generate = True

# Otherwise, the Return parameter list looks different from the Parameters list
napoleon_use_rtype = False
# Otherwise, the Attributes parameter list looks different from the Parameters
# list
napoleon_use_ivar = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
source_suffix = ['.rst']
# source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'MPAS-Analysis'
copyright = u'This software is open source software available under the BSD-3' \
            u'license. Copyright (c) 2022 Triad National Security, LLC. ' \
            u'All rights reserved. Copyright (c) 2018 Lawrence Livermore ' \
            u'National Security, LLC. All rights reserved. Copyright (c) ' \
            u'2018 UT-Battelle, LLC. All rights reserved.'
author = u'Xylar Asay-Davis, Milena Veneziani, Phillip Wolfram, \n' \
         u'Luke Van Roekel, Greg Streletz, Mark Petersen, Stephen Price, \n' \
         u'Joseph Kennedy, Adrian Turner, Matthew Hoffman, Jeremy Fyke'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#

if 'DOCS_VERSION' in os.environ:
    version = os.environ.get('DOCS_VERSION')
    release = version
else:
    # The short X.Y.Z version.
    version = mpas_analysis.__version__
    # The full version, including alpha/beta/rc tags.
    release = mpas_analysis.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store',
                    'design_docs/template.md', 'design_docs/template.rst']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#

# on_rtd is whether we are on readthedocs.org, this line of code grabbed from
# docs.readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']


# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'MPAS-Analysisdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'MPAS-Analysis.tex', u'MPAS-Analysis Documentation',
     author, 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'mpas-analysis', u'MPAS-Analysis Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'MPAS-Analysis', u'MPAS-Analysis Documentation',
     author, 'MPAS-Analysis', 'One line description of project.',
     'Miscellaneous'),
]

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('https://docs.python.org/', None),
    'numpy': ('http://docs.scipy.org/doc/numpy/', None),
    'xarray': ('http://xarray.pydata.org/en/stable/', None),
    'geometric_features':
        ('http://mpas-dev.github.io/geometric_features/stable/', None),
    'mpas_tools':
        ('http://mpas-dev.github.io/MPAS-Tools/stable/', None)}


cwd = os.getcwd()
os.chdir('users_guide')

# Build some custom rst files
xmlFileName = '../../mpas_analysis/obs/observational_datasets.xml'
for component in ['ocean', 'seaice']:
    build_rst_table_from_xml(xmlFileName,
                             f'{component}_obs_table.rst',
                             component)

build_obs_pages_from_xml(xmlFileName)
build_quick_start()

os.chdir(cwd)

for mdFileName in glob('design_docs/*.md'):
    if os.path.basename(mdFileName) == 'template.md':
        continue
    output = m2r2.parse_from_file(mdFileName)
    rstFileName = os.path.splitext(mdFileName)[0]+'.rst'
    with open(rstFileName, 'w') as outFile:
        outFile.write(output)

github_doc_root = 'https://github.com/rtfd/recommonmark/tree/master/doc/'
