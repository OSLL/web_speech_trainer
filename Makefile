-include .env

BASE_VERSION ?= v0.2
BASE_IMAGE ?= dvivanov/wst-base:$(BASE_VERSION)
BASE_DOCKERFILE ?= Dockerfile_base

APP_CONF ?= ../app_conf/config.ini
TESTING_APP_CONF ?= ../app_conf/testing.ini

# groups of tests to run (comma separated, see tests/README.md), empty - all tests
TEST_GROUPS ?=

COMPOSE = docker compose -f docker-compose.yml
COMPOSE_TESTS = docker compose -f docker-compose.yml -f docker-compose-selenium.yml

define image_exists
$(shell docker image inspect $(1) > /dev/null 2>&1 && echo "yes")
endef

export APP_CONF TEST_GROUPS

.PHONY: build-base check-base build build-tests build-all up up-d down tests tests-up unit-tests selenium-tests check-tests

build-base:
	docker build -t $(BASE_IMAGE) -f $(BASE_DOCKERFILE) . ;

check-base:
	@if [ "$(call image_exists,$(BASE_IMAGE))" != "yes" ]; then \
		echo "Trying to pull $(BASE_IMAGE) from remote..." ; \
		if docker pull $(BASE_IMAGE) 2>/dev/null ; then \
			echo "Successfully pulled $(BASE_IMAGE)" ; \
		else \
			echo "Remote image not found or cannot pull. Building locally..." ; \
			$(MAKE) build-base ; \
		fi \
	else \
		echo "$(BASE_IMAGE) already exists" ; \
	fi

build: check-base
	$(COMPOSE) build ;

build-tests:
	$(COMPOSE_TESTS) build selenium-tests ;

build-all: build build-tests

up:
	$(COMPOSE) up ;

up-d:
	$(COMPOSE) up -d ;

down:
	$(COMPOSE_TESTS) down ;

# build and run app with testing config + selenium tests container (tests start automatically)
tests: build-all tests-up

tests-up:
	APP_CONF=$(TESTING_APP_CONF) $(COMPOSE_TESTS) up -d ;

# unit tests inside running web container
unit-tests:
	$(COMPOSE) exec -T -e TEST_GROUPS="$(TEST_GROUPS)" web bash -c 'cd /project/tests && pytest --ignore=selenium' ;

# rerun selenium tests in already running app (container exits after tests)
selenium-tests:
	APP_CONF=$(TESTING_APP_CONF) $(COMPOSE_TESTS) up --no-deps selenium-tests --exit-code-from selenium-tests ;

# wait for selenium tests container to finish and return its exit code
check-tests:
	bash ./tests/scripts/docker_check_tests.sh ;
