# syntax=docker/dockerfile:1.7
#
# Commit-image Dockerfile (SMALL form) — builds ON TOP of the org base image
# (ghcr.io/mayhemheroes/base). The base provides debian + clang/llvm + libFuzzer + Python 3 + the
# identities + the build-contract ENV. ciscoconfparse is a PURE-PYTHON package (with PyPI runtime
# deps), so this image installs the Atheris harness engine (atheris) plus the package and its test
# extra (pytest) into the base system Python as root, then (as the non-root `mayhem` user) compiles
# the ELF launcher shims and runs the real pytest suite via build.sh / test.sh.
#
# Build (from the repo root):
#   DOCKER_BUILDKIT=1 docker build -f mayhem/Dockerfile \
#       --build-arg COMMIT=$(git rev-parse HEAD) \
#       [--build-arg SOURCE_DATE_EPOCH=$(date +%s)] \
#       -t ciscoconfparse-commit:test .

FROM ghcr.io/savantenvs/base:20260621

ARG COMMIT
ARG REPO_URL
# SOURCE_DATE_EPOCH stays an ARG (available to build.sh); never bake it as ENV — an empty value
# breaks clang. build.sh unsets it when empty.
ARG SOURCE_DATE_EPOCH
# Declared for parity with the build contract; ciscoconfparse has no native code to sanitize.
ARG SANITIZER_FLAGS

# Atheris (the libFuzzer harness engine — builds a native module against the base clang/libFuzzer)
# plus the test extra (pytest) go into the base SYSTEM Python. PEP 668 marks that interpreter
# externally-managed, so --break-system-packages. This is the (networked) install step; build.sh
# deliberately does NOT pip-install, so its offline PATCH-tier re-run stays air-gapped. Atheris is
# pinned (3.1.0) for a reproducible engine.
USER root
# pytest is pinned to 7.x: tests/conftest.py stacks @pytest.mark.skipif on a @pytest.fixture
# (cisco_sshd_mocked) — a pattern pytest 8 made a hard error ("Marks cannot be applied to
# fixtures"). Upstream declares pytest >= 7.4.3, so hold at the 7.x line the suite was written for.
RUN pip install --no-cache-dir --break-system-packages atheris==3.1.0 "pytest>=7.4.3,<8"

# Source enters from the build CONTEXT (the CI checkout): the FULL repo (incl. .git history)
# is copied to /mayhem as `mayhem`; build.sh builds in place.
WORKDIR /mayhem
COPY --chown=2000:2000 . /mayhem

# Install ciscoconfparse itself + its PyPI runtime deps (passlib, dnspython, loguru, toml,
# hier_config, deprecated) so the harness/oracle can `import ciscoconfparse`.
RUN pip install --no-cache-dir --break-system-packages .

USER mayhem

# Compile the ELF launcher shims (Mayhem needs an ELF target, not a .py).
RUN bash mayhem/build.sh

# Run the ciscoconfparse real pytest known-answer suite at build time; a failing suite fails build.
RUN if [ -f mayhem/test.sh ]; then bash mayhem/test.sh; else echo "no mayhem/test.sh"; fi

LABEL org.opencontainers.image.source="${REPO_URL}" \
      org.opencontainers.image.revision="${COMMIT}" \
      rlenv.tier="commit" \
      rlenv.source_date_epoch="${SOURCE_DATE_EPOCH}" \
      rlenv.user="mayhem"

USER mayhem
WORKDIR /mayhem
