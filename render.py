#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import yaml
import logging
import jinja2
import shutil
import pathlib
import codecs
import re
import traceback

#-------------------------------------------------------------------------------

version             = "0.0.0"    # version of this program
model               = {}         # the model as parsed from stdin
schema              = "0.0.0"    # the schema version of the model
script_directory    = ""         # the location of the script
templates_directory = ""         # the location of the templates
current_directory   = ""         # the location of the execution environment
output_directory    = ""         # the location of the generated output

# ------------------------------------------------------------------------------
# loadModel: loads yaml model
# ------------------------------------------------------------------------------
def loadModel():
    global model
    global schema
    global script_directory
    global templates_directory

    # A. read yaml from stdin
    yaml_file = ''
    for line in sys.stdin:
        yaml_file += line

    # B. parse yaml into a model
    try:
        model = yaml.safe_load(yaml_file)
    except yaml.YAMLError as exc:
        logging.error('Loading data failed: {}'.format(exc))

        if hasattr(exc, 'problem_mark'):
            logging.error("Error position: (%s:%s)" % (exc.problem_mark.line + 1, exc.problem_mark.column + 1))
        exit(1)

    except Exception as exc:
        logging.error('Loading data failed: {}'.format(exc))
        exit(1)

    # C. derive schema
    if not 'schema' in model:
        logging.error("Model does not have a schema attribute")
        exit(1)

    schema = model['schema']

    # D. derive templates directory and check if it exists
    templates_directory = os.path.join(script_directory, "templates", "V" + schema + "/")

    if not os.path.exists(templates_directory):
        logging.error("Schema '" + schema + "'is not supported")
        exit(1)

# ------------------------------------------------------------------------------
# loadTemplate: loads template from a file and returns a string
# ------------------------------------------------------------------------------
def loadTemplate(filename):
    with codecs.open(str(filename), 'r', 'utf-8') as template_file:
        template = template_file.read()

    return template

# ------------------------------------------------------------------------------
# renderTemplate: apply jinj2 template to model
# ------------------------------------------------------------------------------
def renderTemplate(template_name, template):
    global model

    try:
        # initialize the jinja2 environment
        env = jinja2.Environment(
            trim_blocks=True,
            lstrip_blocks=True,
            extensions=[ 'jinja2.ext.loopcontrols', 'jinja2.ext.do' ]
        )
        env.filters["fixed"]   = fixed_ips_filter
        env.filters["allowed"] = allowed_ips_filter
        env.filters["portmin"] = port_min_filter
        env.filters["portmax"] = port_max_filter

        renderer = env.from_string(template)

        # render a view of the model
        view = renderer.render(model)

        return view

    except jinja2.TemplateSyntaxError as template_error:
        logging.error('Error in template: ' + template_name + '/' + str(template_error.lineno) + ': ' + template_error.message)
        exit(1)

    except jinja2.UndefinedError as exc:
        logging.error('Undefined error in template: ' + template_name + ': {}'.format(str(exc)))
        exit(1)

    except Exception as exc:
        print(traceback.format_exc())
        logging.error('Failed to render model with template ' + template_name + ': {}'.format(str(exc)))
        exit(1)

# ------------------------------------------------------------------------------
# fixed_ips_filter: derives a list of fixed IPs from a string
# format: "fixed: IP1, IP2, IP3, ...;"
# each IP? should either be an IP-address or a
# range with the last octet defining the Range
# e.g. 192.168.178.10-20
# ------------------------------------------------------------------------------
def fixed_ips_filter(str):
  result  = []

  # extract the fixed ips part of the string
  m = re.search( r'fixed\:[^;]*', str, re.IGNORECASE)

  if not m:
    return result

  # get first occurence
  str1 = m[0].strip()

  # remove the prefix: "fixed: "
  str2 = str1[7:]

  # split into substrings
  str3 = str2.split(",")

  # construct the result
  for str4 in str3:
    # check if we have a range
    if str4.find("-") < 0:
      result.append(str4)
    else:
      str5 = generate_ip_range(str4)
      result.extend(str5)

  # completed
  return result

# ------------------------------------------------------------------------------
# allowed_ips_filter derives a list of allowed IPs from a string
# format: "allowed: IP1, IP2, IP3, ...;"
# each IP? should either be an IP-address or a
# range with the last octet defining the Range
# e.g. 192.168.178.10-20
# ------------------------------------------------------------------------------
def allowed_ips_filter(str):
  result  = []

  # extract the allowed ips part of the string
  m = re.search( r'allowed:[^;]*', str, re.IGNORECASE)

  if not m:
    return result

  # get first occurence
  str1 = m[0].strip()

  # remove the prefix: "allowed: "
  str2 = str1[9:]

  # split into substrings
  str3 = str2.split(",")

  # construct the result
  for str4 in str3:
    # check if we have a range
    if str4.find("-") < 0:
      result.append(str4)
    else:
      str5 = generate_ip_range(str4)
      result.extend(str5)

  # completed
  return result

# ------------------------------------------------------------------------------
# port_min_filter derives a min port number from a string
# format: "portmin-portmax|port"
# e.g. 8080-8081
# ------------------------------------------------------------------------------
def port_min_filter(str):
  parts = str.split("-")

  return  (parts[0] if len(parts) == 2 else str)

# ------------------------------------------------------------------------------
# port_max_filter derives a max port number from a string
# format: "portmin-portmax|port"
# e.g. 8080-8081
# ------------------------------------------------------------------------------
def port_max_filter(str):
  parts = str.split("-")

  return  (parts[1] if len(parts) == 2 else str)

# ------------------------------------------------------------------------------
# generate_ip_range generates a list of IP addresses as an array
# ------------------------------------------------------------------------------
def generate_ip_range( ip_range ):
  result = []

  # split range and determine prefix and range
  pos    = ip_range.rfind(".")
  prefix = ip_range[:pos]
  rng    = ip_range[pos+1:]

  # split the range and determine first and last index
  parts = rng.split("-")
  first = int( parts[0] )
  last  = int( parts[1] )

  # construct the result
  for index in range(first,last+1):
    result.append(prefix + "." + str(index) )

  # completed
  return result

# ------------------------------------------------------------------------------
# saveView: save view to a file or a set of files
# ------------------------------------------------------------------------------
def saveView(view, path):
    # check if the view contains special output statement lines:
    # ">> [path] [comments]\n" which advise to output the following
    # data to a file location indicated by the [path] argument

    block     = ''
    file_name = ''
    for line in view.splitlines():
        # determine new filename: ">> [filename] [comments]"
        match = re.match('>> ([^ ]*)(.*)', line)
        if match:
            # write the existing block
            if block != '':
                write_block(str(path), str(file_name), block)

                # reset block
                block = ''

            # set new file name
            file_name = match.group(1)
        else:
            if block == '':
                block = line
            else:
                block += '\n' + line

    # write last block
    write_block(str(path), str(file_name), block)


# --------------------------------------------------------------------------
# write_block: output a block
# --------------------------------------------------------------------------
def write_block(path, file_name, block):
    try:
        # determine path
        if file_name == '':
            file_path = os.path.join(path)
        else:
            file_path = str(pathlib.Path(path).parent)
            file_path = os.path.join(file_path, file_name)

        # check if the file_path does not point to a directory
        if os.path.isdir(file_path):
            logging.error("Destination must not be a directory: {}".format(file_name))
            exit(1)

        # ensure that the directory exists
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # write block as text file
        with codecs.open(file_path, 'w', 'utf-8') as text_file:
            text_file.write(block)

    except IOError as exc:
        snippet_len = 500
        short_block = (block[ :snippet_len ] + '..') if len(block) > snippet_len else block
        logging.error("Error while writing to file {}: \n\n=== SNIPPET START (first {} chars)=== \n{}\n===SNIPPET END===".format(file_name, snippet_len, short_block))
        exit(1)

#-------------------------------------------------------------------------------

def main():
    global script_directory
    global current_directory
    global output_directory

    # determine path of module
    script_directory = os.path.dirname(os.path.realpath(__file__))

    # determine current working directory
    current_directory = os.getcwd()

    # define output directory
    output_directory = os.path.join(current_directory, "output") + "/"

    # cleanup output path
    shutil.rmtree(output_directory, ignore_errors=True, onerror=None)

    # load model
    loadModel()

    # load yaml model and render all templates
    try:
        # find every template
        for filename in pathlib.Path(templates_directory).glob('**/*.j2'):
            if filename.is_dir():
                continue

            # define template name
            template_name = str(filename).replace( templates_directory, "" )

            # # load template
            template = loadTemplate(filename)

            # render template
            view = renderTemplate(template_name, template)

            # remove the ".j2" extension
            basename = str(filename)[:-3]

            # define output path
            output_path = str(basename).replace( templates_directory, output_directory )

            # save view
            saveView(view, output_path)

    except Exception as exc:
        traceback.print_exc()
        logging.error('Unknown error: {}'.format(exc))
        return 1

    return 0

#-------------------------------------------------------------------------------

if __name__ == "__main__":
    main()

#-------------------------------------------------------------------------------
