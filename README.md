# Workflow: HTTP/3 censorship measurements with URLGETTER

## Input generation

### 0. Run all steps.
- ```input_generator.py [-h] -m MINIOONI_PATH -l LISTDIR -cc COUNTRYCODE -t TARGETDIR [-g] [-c COLUMN] [-v]```
- use ```-g``` to use both local country list as well as global list (which must be generated first)
- result: ```targetdir/<COUNTRYCODE>[_global]_http3_filtered_cacheddns.txt``` with lines like this: ```url-----ip```

### 1. Extract urls
**Extract urls from csv source. [citizenlab test-lists](https://github.com/citizenlab/test-lists)**
- clone source repo
- optional: use prune-dead-urls.py script
- run: ```generate_txt_input.py [-h] -cc COUNTRYCODE -t TARGETDIR [-c COLUMN] [-r ROOTDIR]```
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
**Filter out domains from the following categories: "XED", "GAYL", "PORN", "PROV", "DATE", "MINF", "REL", "LGBT"**
- run: ```filter_categories.py [-h] -i INPUTURLS -l LOCALPATH -t TARGETDIR [-g GLOBALPATH]```
- result: ```targetdir/<COUNTRYCODE>_http3.txt.filtered.txt```

### 5. Resolve IP addresses
**Resolve domain names by querying dot://8.8.8.8 (Google DNS)**
- run ```resolve.py [-h] -i INPUTFILE -p PREFIX -t TARGETDIR``` 
- result: ```targetdir/[PREFIX]_cacheddns.txt``` with lines like this: ```url-----ip```

<br>
<br>

## Run the measurement

### 1. Download latest probe-cli release
- https://github.com/ooni/probe-cli/releases
- ```probe-cli/internal$ go build ./cmd/miniooni```

### 2. Runner script
- ```runscript.py [-h] -u URLS -p MINIOONI_PATH```, where URLS is the generated input file and MINIOONI_PATH leads to the location of the miniooni executable (```internal/miniooni```)

- on remote machine: 
  ```torsocks ssh HOST```
  ```nohup python3 runscript.py -u URLS.txt -p ./miniooni &```

<br>
<br>

## Examine and visualize the results

### Filter measurements
**Print URL, step and failure type of filtered measurements**
- ```filter.py [-h] -F FILE [-s STEPS] [-u INPUTURL] [-ip IP] [-t FAILURETYPE] [-f] [-c] ```
- use filter ```-s``` to only examine certain measurement steps, e.g. "tcp_cached"
- use filter ```-u``` to investigate measurements of a specific URL
- use filter ```-ip``` to investigate measurements of a specific IP address
- use filter ```-t``` to only examine certain failure types, e.g. "TLS-hs-to"
- use filter ```-f``` to only examine failed measurements
- use ```-c``` to print cummulative result at the end


### Visualize data correlation
***Generate a sankey diagram that depicts the correlation between different urlgetter measurement steps**
- ```eval.py [-h] -F FILE -s STEPS [-o OUTPATH]```
- the file(s) to be evaluated are defined by the ```-F``` parameter; this can be a file or a folder
- use ```-s``` to define the 2 steps that are compared, e.g. "tcp_cached quic_cached"
- to define the output directory use the ```-o``` option


  