# fmpstack Vision

fmpstack lets one captain operate a reliable coding fleet by combining Firstmate's fleet orchestration with a small pstack-inspired engineering discipline inside each worker.
The product is a calm, accountable way to turn one captain's intent into evidence-backed work across projects without making the captain manage a room full of agent sessions.
This is a product boundary and a test for future choices, not a changelog of inherited features or an implementation manual.

## One captain and one router

The captain has one interface and one point of accountability: Firstmate.
Firstmate alone owns intake, project selection, task shape, isolation, supervision, delivery, and enforcement of the merge-authority boundary under captain-configured policy.
The captain retains merge authority unless explicit autonomy has been granted, and Firstmate may merge only within that explicit policy.
Workers report through Firstmate, while captain-facing communication stays focused on outcomes, consequences, decisions, and risks.
Authority is explicit rather than inferred, and evidence or recommendations never become permission by themselves.

A worker receives a ship or scout task only after Firstmate has routed it and established its project, isolated working space, delivery path, and authority boundaries.
Only then does the fmpstack inner loop begin, and it remains local to that task until the worker returns its result to Firstmate.
The loop never routes work, selects projects, creates fleet isolation, supervises other workers, chooses delivery, or merges anything.
Firstmate's selected delivery path remains the only review and shipping ceremony.

## The worker's engineering discipline

The discipline is deliberately small and enduring:

- Subtract before adding by seeking the smallest change or investigation that meets the task and reusing existing paths.
- Identify the input, state, output, and blast radius before changing the artifact.
- Walk unfamiliar or shared boundaries only when warranted by the task, and avoid architecture theater on ordinary local work.
- Reproduce defects on the affected surface and trace their causes before changing them.
- Prove the real artifact with a live command, user flow, record, or focused verifier before declaring success.

A scout applies the same discipline to investigation and reports evidence and verification gaps instead of pretending that a recommendation is a change.
The discipline is harness-neutral because it is a task contract, not an integration with one worker vendor.

## Durable operating principles

The fleet serves exactly one captain, preserves explicit authority, and keeps obligations durable and restart-safe.
Work, promises, decisions, and required follow-up survive conversation loss through records that can be reconciled rather than remembered.
Deterministic mechanics should own exact, repeatable operations, while agents apply judgment where understanding and interpretation are required.
The system remains vendor-neutral, introspectable, and simple enough for one captain to own and adapt.
Every added capability must earn its place by improving reliable outcomes or reducing captain attention without adding a competing authority.

## What fmpstack is not

fmpstack does not vendor pstack or reproduce its plugin, model router, or broader playbook catalog.
It does not add a second router, review ceremony, shipping ceremony, or shipping authority.
It does not depend on one worker harness, model, runtime, or session manager.
It is not a model, plugin, MCP server, or hosted fleet application.
It is not a replacement for Firstmate's operating contract, delivery paths, supervision, or merge policy.

## Choosing future changes

A change belongs in fmpstack when it strengthens the single-captain experience, makes Firstmate's fleet boundary more reliable, or makes the task-local engineering result smaller, clearer, more reproducible, or better proven.
A change does not belong when it duplicates Firstmate ownership, widens worker authority, couples the discipline to a vendor, adds ceremony without evidence, or makes the hybrid harder to understand and operate.
The hybrid exists because fleet-level coordination and task-level engineering discipline solve different problems, and keeping their boundary sharp makes both more reliable.
