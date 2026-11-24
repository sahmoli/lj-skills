# lj-skills check harness — stdlib + optional PyYAML, offline.
# Keep matplotlib off ~/.matplotlib so the test gate cannot Abort trap: 6.
export MPLCONFIGDIR ?= $(CURDIR)/.mplconfig
$(shell mkdir -p "$(MPLCONFIGDIR)")
.PHONY: check audit test selftest hook

check:        ## release gate: structure/routing/content lint + behavioral validator tests
	@python3 lint/run_checks.py
	@python3 -m unittest discover -s tests

audit:        ## full: also list every WARN and rank the re-verify worklist
	@python3 lint/run_checks.py --strict

selftest:     ## structural/routing/guardrail regression + test-your-test only
	@python3 lint/run_checks.py --selftest-only

test:         ## unittest form of the self-tests
	@python3 -m unittest discover -s tests -v

hook:         ## install the pre-commit hook into this repo's .git
	@ln -sf ../../hooks/pre-commit .git/hooks/pre-commit && echo "pre-commit hook linked."
