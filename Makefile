.PHONY: dev build clean

dev:
	hugo server --buildDrafts

build:
	hugo --minify

clean:
	rm -rf public/ resources/
