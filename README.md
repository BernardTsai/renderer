renderer
========

A simple python3 script which renders a yaml model into a set of files (as shown in the diagram below) by:

1. reading a **yaml model** from stdin,
2. determining the top-level **schema** attribute,  
3. searching for a matching subdirectory in the **templates** subdirectory,
4. applying all **jinj2 templates** it finds there and
5. then writing the results into corresponding files (without the .j2 extension) of an **output** directory which is created as a subfolder of the current working directory.


````
             templates/<schema>/....
                     |
                     |
                     v
yaml (schema) ==> render.py ==> ./output/...

````

To invoke the renderer issue following command:

````
> cat model.yml | ./render.py
````

The templates can make use of a special tweak which allows to generate several output files from one template by adding following information into the templates:

````
...
>> [relative filename]
...
````

When the renderer finds such a line in the text it will concatenate the original output path with the relative filename and output all following lines to the corresponding file. 

Generating multiple output files can be achieved by e.g. enclosing such a line in a jinj2 loop and by deriving the filename from the model.  

Author: Bernard Tsai (bernard@tsai.eu)
