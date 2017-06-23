# Test Proposed

The purpose of this is to complete further testing on the Ubuntu Server packages that are found in the proposed release.

## Overview

First, given a release (e.g. xenial) the script goes and checks for any new source packages uploaded to proposed in the last day. If none are found, exit.

If any source packages are new to proposed, the security team's automated testing repo is downloaded and checked for any tests that can be ran against binaries in the new source package uploaded for testing.

Finally, a VM is created for the release of interest, the package is installed from proposed, and tests run.
