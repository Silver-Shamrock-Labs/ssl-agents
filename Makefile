.PHONY: build clean

DIST_DIR := dist
ZIP      := $(DIST_DIR)/lambda.zip

build: clean
	mkdir -p $(DIST_DIR)/package
	pip install -r requirements.txt -t $(DIST_DIR)/package --quiet
	cp -r slack $(DIST_DIR)/package/
	cp apps.yaml $(DIST_DIR)/package/
	cd $(DIST_DIR)/package && zip -r ../lambda.zip . -x "*.pyc" -x "*/__pycache__/*"
	rm -rf $(DIST_DIR)/package
	@echo "Built $(ZIP)"

clean:
	rm -rf $(DIST_DIR)
