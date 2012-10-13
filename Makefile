all: out/main.css
out/%.css: web/%.less
	mkdir -p $(@D)
	lessc $< $@
out/%.js: web/%.coffee
	mkdir -p $(@D)
	coffee -b -c -o $(@D) $<
