# Run hg purge & git clean, but exclude secrets and other dev env files
clean:
	hg purge --all \
	   --exclude 'secrets*.py' \
	   --exclude '.tags*' \
	   --exclude 'deploy/node_modules'
	cd khan-exercises && git clean -xdf

# Run unittests.  If COVERAGE is set, run them in coverage mode.
COVERAGE_OMIT = *_test.py
COVERAGE_OMIT += */google_appengine/*
COVERAGE_OMIT += agar/*
COVERAGE_OMIT += api/packages/*
COVERAGE_OMIT += asynctools/*
COVERAGE_OMIT += atom/*
COVERAGE_OMIT += gdata/*
COVERAGE_OMIT += jinja2/*
COVERAGE_OMIT += mapreduce/*
COVERAGE_OMIT += tools/*
COVERAGE_OMIT += webapp2.py
COVERAGE_OMIT += webapp2_extras/*
check:
	if test -n "$(COVERAGE)"; then  \
	   coverage run --omit="`echo '$(COVERAGE_OMIT)' | tr ' '  ,`" \
	      tools/runtests.py --xml && \
	   coverage xml && \
	   coverage html; \
	else \
	   python tools/runtests.py; \
	fi

# Run lint checks
lint:
	tools/runpep8.sh

# Run unit tests with XML test and code coverage reports

# Run the tests we want to run before committing.  Once you've run
# these, you can be confident (well, more confident) the commit is a
# good idea.
precommit: lint check ;


# Compile handlebars templates
handlebars:
	python deploy/compile_handlebar_templates.py

# Compile jinja templates
jinja:
	python deploy/compile_templates.py

# Pack exercise files
exercises:
	ruby khan-exercises/build/pack.rb

# Compress javascript
js:
	python deploy/compress.py js

# Compress css
css:
	python deploy/compress.py css

# Package less stylesheets
less:
	python deploy/compile_less.py
