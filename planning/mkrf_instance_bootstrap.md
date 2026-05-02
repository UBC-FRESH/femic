# MKRF Instance Bootstrap Notes

Issue: `#171`

## Summary

Bootstrap `UBC-FRESH/femic-mkrf-instance` as a private standalone FEMIC
instance repository using the TSA29-style large-only DataLad/git-annex pattern.

This first slice is intentionally thin:

- create the private GitHub repo;
- scaffold the standard FEMIC instance skeleton for `mkrf`;
- keep docs, config, runbooks, rebuild metadata, and other small canonical
  text in Git;
- annex only a deliberate non-sensitive smoke artifact for publication-path
  validation;
- create a dedicated private-first Arbutus bucket and wire it as the named
  `arbutus-s3` special remote;
- prove cold-clone enable/get behavior; and
- link the instance back into the parent FEMIC repo as
  `external/femic-mkrf-instance`.

## Explicit Defaults

- GitHub home: `UBC-FRESH`
- visibility: private
- storage model: large-only DataLad/git-annex instance repo
- first published milestone: thin baseline only
- bucket name: `ubc-fresh-femic-mkrf-instance`
- special remote name: `arbutus-s3`

## Scope Boundary

Out of scope for this slice:

- publishing the current bulky MKRF payload;
- adding MKRF to packaged built-ins;
- adding MKRF to public sample-instance docs; and
- GitHub Pages / standalone docs hosting.
