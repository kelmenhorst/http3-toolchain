# Workflow: HTTP/3 censorship measurements with URLGETTER

## [Input generation](preprocessing)

### 0. Run all steps.
- ```input_generator.py [-h] -cc COUNTRYCODE -t TARGETDIR [-g] [-v]```
- use ```-g``` to use both local country list as well as global list (which must be generated first)
- result: ```targetdir/<COUNTRYCODE>[_global]_http3_filtered_cacheddns.txt``` with lines like this: ```url-----ip```

### 1. Extract urls
**Extracts url strings from csv tables in [citizenlab test-lists](https://github.com/citizenlab/test-lists)**
- run: ```generate_txt_input.py [-h] -cc COUNTRYCODE -t TARGETDIR```
- result: ```targetdir/<COUNTRYCODE>.txt```

### 2. Check HTTP/3 compatibility
**Filter urls for HTTP/3 support.**
- download latest probe-cli release
- run: ```check_http3.py [-h] -i INPUTFILE -t TARGETDIR [-v]```
- result: ```targetdir/<COUNTRYCODE>_http3.txt```

### 3. Aggregate (optional)
**Combine global and countryspecific lists.**
- run: ```aggregate.py [-h] FILE1 FILE2 [FILE3 ...]```
- result: ```targetdir/<COUNTRYCODE1]_http3_<COUNTRYCODE2>_http3.txt```

### 4. Filter risky categories
**Filter out domains from certain content categories.**
- as ```-c``` parameter I use: "XED GAYL PORN PROV DATE MINF REL LGBT"
- run: ```filter_categories.py [-h] -i INPUTURL_FILE_PATH -cc COUNTRYCODE -t TARGETDIR -c CATEGORIES [-g]```
- result: ```targetdir/<COUNTRYCODE>_http3.txt.filtered.txt```

### 5. Resolve IP addresses
**Resolve domain names by querying dot://8.8.8.8 (Google DNS)**
- run ```resolve.py [-h] -i INPUTFILE -p PREFIX -t TARGETDIR``` 
- result: ```targetdir/[PREFIX]_cacheddns.txt``` with lines like this: ```url-----ip```

<br>
<br>

## [Run the measurement](runscript.py)

### 1. Download latest probe-cli release
- https://github.com/ooni/probe-cli/releases
- ```probe-cli/internal$ go build ./cmd/miniooni```
- Initialize ```miniooni``` by consenting to the risks of running OONI, e.g. with this command: <br/>
```./miniooni --yes -i https://ooni.org urlgetter```

### 2. Runner script
- ```runscript.py [-h] -u URLS -p MINIOONI_PATH```, where URLS is the generated input file and MINIOONI_PATH leads to the location of the miniooni executable (```internal/miniooni```)

- on remote machine: 
  ```torsocks ssh HOST```
  ```nohup python3 runscript.py -u URLS.txt -p ./miniooni &```

<br>
<br>

## [Examine and visualize the results](evaluation)
**Sanity checks** <br/>
For the evaluation script, you can add a postprocessing sanity check. The base of the sanity check is a json(l) file which contains a measurement taken in a trusted (i.e. uncensored) network using the same input as the analyzed meausurement(s). The idea is that, if servers have malfunctions or their QUIC support is unstable, it shows up as a failure in an uncensored network and should be filtered out from the measurements. Momentary malfunctions are not filtered out with this mechanism.



### Visualize data correlation
**Generate a sankey diagram that depicts the correlation between different urlgetter measurement steps**
- ```eval.py MODE [-h] -f FILE [-c SANITYCHECK] [-o OUT] [-v] [-S SANKEY] [-C FILTERS]```
- ```MODE``` is the evaluation mode to use, currently it can be one of "sankey", "consistency", "throttling", "runtimes", "print-details", "print-urls" (see below)
- the file(s) to be evaluated are defined by the ```-f``` parameter; this can be a file or a folder
- use ```-c``` to specify a file for a sanity check (see above, Sanity check)
- use ```-o``` to define an output file name to save the result
- use ```-v``` to show verbose output
- use ```-S``` to specify the name of a .json file with the filters for the two compared classes of measurements, only works with MODE "sankey",  see [examples/sankey_classes.json](examples/sankey_classes.json). [examples/filter_classes.json](examples/filter_classes.json) contains the full list of supported filters.
- use ```-C``` to specify the name of a .json file with the filters for the (multiple) compared classes of measurements, only works with MODEs "consistency", "throttling" and "runtimes", see [./examples/filter_classes.json](examples/filter_classes.json) for a full list of supported filters.

#### **Example usage: Sankey**
Generate a **sankey flow** diagram to compare the results of **HTTPS and HTTP/3** urlgetter measurements (annotated with ```urlgetter_step=tcp_cached/quic_cached```) in **AS45090** for all measurement files in the **folder** ```./folder```, and **store** the resulting diagram in ```example.pdf```. Use the **sanity check** file (same measurements taken from a trusted network) stored in ```./sanity_check.jsonl```
```
python3 eval.py sankey -f ./folder -S ../examples/sankey_classes.json -c ./sanity_check.jsonl -o example.pdf
```
Result: 
![sankey example](examples/sankey.png)


#### **Example usage: Consistency**
- Generate a **CDF function** of the consistency of urlgetter HTTPS and HTTP/3 as well as quicping measurements in **AS45090** for all measurement files in the folder ```./folder``` and store the resulting diagram in example.pdf.
```
python3 eval.py consistency -f ./folder -C ../examples/filter_classes.json -o example.pdf
```
Result:
![consistency example](examples/consistency.png)