# Implementation notes for a no-GUI Patchworks interface in FEMIC

This is now an active tracked task:

- Governing GitHub issue: `#54`
- Governing roadmap phase: `P49`
- Working branch: `feature/patchworks-headless-runner`

Immediate implementation target:

- prove the smallest real FEMIC-controlled headless Patchworks seam:
  - launch Patchworks against a target `.pin`
  - suppress the classic GUI path
  - run one unattended scenario to completion
  - write output/report artifacts to disk
  - return control cleanly without a human click loop

Do not over-scope the first slice. A minimal unattended run/report/exit proof
is enough to land the seam before broader scenario-definition helpers are
added.

Current status after the latest proving-ground smokes:

- the no-GUI launch seam is real and FEMIC can drive it;
- the proving-ground model loads fully and `PatchWorks_Init` completes in
  headless mode;
- FEMIC now supervises Windows headless runs directly instead of launching them
  blindly and waiting forever;
- FEMIC watches the headless trace/log outputs for explicit success/failure
  markers and self-terminates Patchworks Java trees automatically in either
  case;
- this removes the human babysitting problem for dead failed runs;
- the critical scheduler insight is now confirmed:
  in the proving-ground BeanShell path, `waitForIterations(...)` should own
  scheduler startup; pre-issuing `control.resume()` triggers the old
  `java.lang.IllegalStateException: Not suspended` seam;
- with that fix in place, a real proving-ground unattended run now completes,
  saves a stage, and returns control cleanly.

Current implementation order:

1. Reuse FEMIC's existing BeanShell launcher in
   `src/femic/patchworks_runtime.py`.
2. Generate a tiny BeanShell wrapper that calls
   `AppChooser.invoke("ca.spatial.patchworks.Patchworks", ..., true)` with the
   target `.pin` and a small FEMIC headless argument contract.
3. Teach the proving-ground K3Z analysis surface to parse `args`, skip
   `classic_GUI(control)` when FEMIC headless mode is requested, still
   register reports, and then run a bounded analyze/save cycle before
   returning.
4. Prove the first slice only on
   `analysis/base.pin`.

The first slice should not attempt to solve the whole scenario-definition
problem. A bounded analyze/save cycle with real reports on disk is enough to
prove the no-GUI seam before broadening into richer headless scheduling
helpers.

Current status after the latest proving-ground smokes:

- the first successful save-stage proof (`p49_smoke_20260328k`) turned out to
  be a passive default-state save because `scenario/schedule.csv` was empty;
- FEMIC now supports a tiny headless scenario mode,
  `max-even-flow-smoke`, that activates one existing target and applies a
  modest minimum annual value before the bounded wait/save cycle;
- direct targeting of `flow.even.product.Yield.managed.Total` did not produce a
  useful schedule, but activating the underlying
  `product.Yield.managed.Total` target did;
- real proving-ground smoke `p49_smoke_20260328p` now proves a full
  no-GUI scenario step:
  - `targetStatus.csv` records `product.Yield.managed.Total` as active;
  - `targetSummary.csv` shows non-zero managed-yield currents plus derived
    `flow.even.product.Yield.managed.Total` values;
  - `schedule.csv` is non-empty and contains real managed treatments;
  - FEMIC still saves the stage and returns control cleanly without human
    cleanup.
- one more headless scheduler insight is now confirmed:
  - to activate the real `flow.even.*` companion safely, the proving-ground
    helper must first seed the underlying harvest target for an initial wait
    phase, then suspend, then activate the companion target, and only then run
    the second wait phase;
  - real proving-ground smoke `p49_smoke_20260328q` proves that two-phase
    pattern:
    - both `product.Yield.managed.Total` and
      `flow.even.product.Yield.managed.Total` are active in
      `scenario/targetStatus.csv`;
    - `targetSummary.csv` shows non-zero currents for both targets;
    - `schedule.csv` remains non-empty (677 lines) with real managed
      treatments; and
    - FEMIC still saves the stage and self-terminates Patchworks cleanly.
- the normal CLI/default-target path is also now proven:
  - real proving-ground smoke `p49_smoke_20260328r` omitted an explicit
    scenario target and relied on FEMIC's default
    `product.Yield.managed.Total` resolution;
  - both the underlying harvest target and the `flow.even.*` companion still
  ended up active in `scenario/targetStatus.csv`; and
  - `schedule.csv` stayed non-empty (788 lines), so the working seam is not
    limited to a hand-crafted target override.
- the authoritative closeout proof now comes from the real base K3Z variant:
  - proving-ground smoke `p49_base_closeout_20260328a` used `analysis/base.pin`
    with the useful default recipe:
    - seed harvest first via `product.Yield.managed.Total`;
    - set the even-flow companion target to min=max=`0` with
      min=max weight=`100` in all periods;
    - let `waitForIterations(...)` run `50000 + 50000` iterations across the
      seed and even-flow phases;
  - `targetStatus.csv` recorded:
    - `product.Yield.managed.Total` active; and
    - `flow.even.product.Yield.managed.Total` active with both min/max mode
      enabled;
  - `targetSummary.csv` showed:
    - nearly level even-flow deviations around zero; and
    - strong non-zero underlying managed-yield currents around 69,000 by
      period;
  - `schedule.csv` remained non-empty (341 lines), so the seam now has a real
    useful base-K3Z proof, not just an intensive proving-ground surrogate.

That means the proving-ground headless seam is no longer just a save-stage
novelty; it can now execute a small real scheduling smoke and persist the
results for downstream inspection.

Most recent high-value proof point:

- run id: `p49_smoke_20260328j`
- target:
  `analysis/intensive_light_standstructure.pin`
- result:
  - launch/load/init succeeded in headless mode;
  - FEMIC trace reached the headless worker/analyze path;
  - `control.waitForIterations(1)` completed successfully once explicit
    `control.resume()` was removed from the headless helper;
  - the headless helper then suspended the scheduler, called `saveStage`, and
    wrote:
    - `analysis/headless_runs/p49_smoke_20260328j`
  - the manifest reported:
    - `returncode=0`
    - `terminal_state=success`
    - `saved_file_count=1695`
  - FEMIC detected the success marker and then terminated the Java process tree
    automatically, so no human cleanup was required.

From Patchworks API docs:

"""
User interface

You may be surprised to know that the Patchworks user interface is optional and is activated by a method call within the PatchWorks_Init function:

classic_GUI(control);
The classic_GUI function takes one parameter, which is the global variable control, a reference to the Control object. This function builds the menus, toolbars, and lays out all of the components that are visible in the Patchworks main window. If you remove or comment out this line, the user interface will not be displayed.

Displaying the user interface seems like a good thing; why would you ever choose not to do this? Well, there are a few situations where you might take a different approach:

You could build your own user interface using the Java Swing toolkit and the Patchworks API components. This is a possibility, but for most people, it would be a heroic undertaking.

Without the user interface, you can run Patchworks in unattended batch mode: the PatchWorks_Init function will run to completion, and then the application will exit. In this case, the function can contain commands to start an analysis, let it run until convergence, and perform any post-analysis wrap-up tasks.

Again, why would you want to do this? This approach would be a nice automation if you need to carry out pre-processing steps before running Patchworks. We will take a look at this in the section called “Invoke Patchworks from a script”.
"""

which references this section:

"""
Invoke Patchworks from a script

So far, we have only tried using the Application Launcher to start Patchworks. There may be situations where you would want to start Patchworks under program control, perhaps to automate the generation of custom input datasets. The BeanShell and Java platforms make it easy to launch and control other applications, and the Patchwork API has a tool that makes this even easier.

AppChooser.invoke("ca.spatial.patchworks.Patchworks",  1
   new String[] {                                      2
      basename+"/analysis/rangeAssessment.pin",        3
      "highYield",
      15                                               4
   },
   true
);
In this example:

1

The Appchooser.invoke method is called to start the Patchworks application in a new process. The first argument to the invoke method is the name of the class that will be invoked.

2

The list of arguments to the Patchworks model is passed as an array of string variables. The string array constructor prepares the space for this list.

3

The arguments to the Patchworks program are provided as the elements of the array. The first argument must be the fully qualified name of the PIN file that will be loaded.

4

The final argument to the invoke method is a boolean flag to indicate if the calling script should wait until the application has finished running. In this case, we have selected true, and the calling application will not proceed until the Patchworks process has exited.

This command will start a new instance of the Patchworks program. The first argument that is passed in must be the fully qualified name of the PIN file to use to load the model. At this stage, any relative path would be relative to the default working directory of the application.

When Patchworks is invoked, all of the passed-in arguments are available in a global variable named args, which is an array of strings, the same as those passed into the invoke method. The first value in the argument list will be used as the name of the PIN file to load. Within the PIN, file the other values in the args array may be extracted and used to adjust file names and other parameters.

It is possible to use conditional tests to set up a PIN file that is suitable for batch mode and interactive use. The following code fragment shows how to test if values are available in the args array, and if not, then use a default or prompt for a replacement:

useBatch = false;
scenarioName = "default";
ageDelay = 0;
if (args.length == 3) {
   useBatch = true;
   scenarioName = args[1];
   ageDelay = Integer.parseInt(args[2]);
}
In the above code, the helper variables are first set to default values. Then, if the args array has the required number of parameters, the helper values are overridden with the passed-in arguments.

The Appchooser.invoke method is used to launch programs from the Patchworks toolkit. Java has a general purpose process-launching tool that can be used for external programs.

"""

So there is *already a clear documented path* to run patchworks in unsupervised headless mode. We just need to wire this into FEMIC and Bob is our uncle once again.
