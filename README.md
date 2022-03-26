# Workflow: HTTP/3 censorship measurements with URLGETTER

## Requirements

**Minimum requirements for simple analysis:** <br/>
```pip3 install -r evaluation/min_requirements.txt```

**All requirements:** <br/>
```pip3 install -r requirements.txt```

## [Input generation](preprocessing)

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

## [Examine and visualize the results](evaluation)