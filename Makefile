.PHONY: test demo
test: ; python -m unittest discover -s tests -t . -v
demo: ; python -m exitkit demo
