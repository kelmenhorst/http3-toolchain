# Workflow: HTTP/3 censorship measurements with URLGETTER

## Input generation

### 1. Prepare input
**Extract urls from csv source. [citizenlab test-lists](https://github.com/citizenlab/test-lists)**
- clone source repo
- optional: use prune-dead-urls.py script
- run: ```generate_txt_input.py [-h] -cc COUNTRYCODE -t TARGETDIR [-c COLUMN] [-r ROOTDIR]```
- result: ```targetdir/[COUNTRYCODE].txt```

### 2. Check HTTP/3 compatibility
**Filter urls for HTTP/3 support.**
- download latest probe-cli release
- run: ```check_http3.py [-h] -i INPUTFILE -m MINIOONI_PATH -t TARGETDIR```
- result: ```targetdir/[COUNTRYCODE]_http3.txt```

### 3. Aggregate (optional)
**Combine global and countryspecific lists.**
- run: ```aggregate.py [-h] FILE1 FILE2 [FILE3 ...]```
- result: ```targetdir/[COUNTRYCODE1]_http3_[COUNTRYCODE2]_http3.txt```

### 4. Filter risky categories
**Filter out domains from the following categories: "XED", "GAYL", "PORN", "PROV", "DATE", "MINF", "REL", "LGBT"**
- run: ```filter_categories.py [-h] -i INPUTURLS -l LOCALPATH -t TARGETDIR [-g GLOBALPATH]```
- result: ```targetdir/[COUNTRYCODE]_http3.txt.filtered.txt```

### 5. Resolve IP addresses
**Resolve domain names by querying dot://8.8.8.8 (Google DNS)**
- run ```resolve.py [-h] -i INPUTFILE -p PREFIX -t TARGETDIR``` 
- result: ```targetdir/[PREFIX]_cacheddns.txt``` with lines like this: ```url-----ip```


## Run the measurement

### 1. Download latest probe-cli release
- https://github.com/ooni/probe-cli/releases
- ```probe-cli/internal¼ go build ./cmd/miniooni```

### 2. Runner script
- ```runscript.py [-h] -u URLS -p MINIOONI_PATH```, where URLS is the generated input file and MINIOONI_PATH leads to the location of the miniooni executable (```internal/miniooni```)


## Postprocess
- ```eval_better.py``` ?





________________

### 2b. Check HTTP/3 compatibility
**Filter urls for HTTP/3 support.**
- download latest probe-cli release
- add this code to ```experiment/urlgetter/urlgetter.go```
   ```
   [tk, err := g.Get(ctx)]
	fmt.Println(err)
	if err == nil {
		f, _ := os.OpenFile("temp.txt", os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0600)
		defer f.Close()
		f.WriteString(string(measurement.Input) + "\n")
	}
    ```
- add this code to ```internal/cmd/miniooni/main.go```
  ```
  ioutil.WriteFile("temp.txt", []byte("\n"), 0644)
  [Main()]
  ```
- build latest probe-cli release: ```go build ./internal/cmd/miniooni/```
- run ```./miniooni -f ../../domains/txts/[COUNTRYCODE]_urls.txt -O HTTP3Enabled=true -n -N urlgetter```