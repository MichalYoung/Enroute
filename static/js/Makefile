#
# Build bundled distribution files from javascript sources 
#

LIBS = node_modules/*/dist/*
OPTS = --debug
# A locally installed copy of browserify
BROWSERIFY=node_modules/browserify/bin/cmd.js

enroute:  dist/enroute.js

dist/enroute.js:  enroute.js $(LIBS)
	$(BROWSERIFY) enroute.js $(OPTS) -o dist/enroute.js

install: 
	rm -rf node_modules
	mkdir node_modules
	npm install leaflet
	npm install browserify
	npm install moment
	npm install maki
	rm -rf dist
	mkdir dist
	make enroute 

clean: 
	rm -rf node_modules
	rm -rf dist
