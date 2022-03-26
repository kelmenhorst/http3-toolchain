# Input generation for HTTP/3 measurements

## 0. Run all steps.
- ```input_generator.py [-h] -cc COUNTRYCODE -t TARGETDIR [-g] [-v]```
- use ```-g``` to use both local country list as well as global list (which must be generated first)
- result: ```targetdir/<COUNTRYCODE>[_global]_http3_filtered_cacheddns.txt``` with lines like this: ```url-----ip```

## 1. Extract urls from Citizenlab test lists
**Extracts url strings from csv tables in [citizenlab test-lists](https://github.com/citizenlab/test-lists)**
- run: ```generate_txt_input.py [-h] -cc COUNTRYCODE -t TARGETDIR```
- result: ```targetdir/<COUNTRYCODE>.txt```

## 2. Check HTTP/3 compatibility
**Filter urls for HTTP/3 support.**
- download latest probe-cli release
- run: ```check_http3.py [-h] -i INPUTFILE -t TARGETDIR [-v]```
- result: ```targetdir/<COUNTRYCODE>_http3.txt```

## 3. Aggregate (optional)
**Combine global and countryspecific lists.**
- run: ```aggregate.py [-h] FILE1 FILE2 [FILE3 ...]```
- result: ```targetdir/<COUNTRYCODE1]_http3_<COUNTRYCODE2>_http3.txt```

## 4. Filter risky categories
**Filter out domains from certain content categories.**
- as ```-c``` parameter I use: "XED GAYL PORN PROV DATE MINF REL LGBT"
- run: ```filter_categories.py [-h] -i INPUTURL_FILE_PATH -cc COUNTRYCODE -t TARGETDIR -c CATEGORIES [-g]```
- result: ```targetdir/<COUNTRYCODE>_http3.txt.filtered.txt```

## 5. Resolve IP addresses
**Resolve domain names by querying dot://8.8.8.8 (Google DNS)**
- run ```resolve.py [-h] -i INPUTFILE -p PREFIX -t TARGETDIR``` 
- result: ```targetdir/[PREFIX]_cacheddns.txt``` with lines like this: ```url-----ip```