"""
Onboard an additional ("producer") GCP project to the central VeriForge Ops
Pub/Sub topic by creating a cross-project Log Router sink.

Architecture (centralized log lake):

    Producer Project B ──[Log Router sink]──┐
    Producer Project C ──[Log Router sink]──┤
                                            ▼
                       Central Project A topic: veriforgeops-telemetry-ingest
                                            │
                                            ▼
                              subscription(s) → UI / read_pubsub_logs.py

Each producer project gets its own sink whose destination is the SAME central
topic. Pub/Sub fan-out then lets one (or many) subscriptions consume the merged
stream from all onboarded accounts.

This script performs the parts that live in the PRODUCER project:
  1. Create the sink (destination = central topic).
  2. Read back the sink's writer-identity service account.

It then PRINTS — but does NOT execute — the IAM binding that must be applied on
the CENTRAL project's topic, because granting roles/pubsub.publisher modifies
access control and should be reviewed/run with central-project credentials:

  gcloud pubsub topics add-iam-policy-binding <TOPIC> \
      --member='<WRITER_IDENTITY>' --role='roles/pubsub.publisher' \
      --project=<CENTRAL_PROJECT>

Usage:
  python configure_cross_project_sink.py \
      --producer-project cog01k0vzzgbxmhbwwp8haem80fxr \
      --producer-account soham.ganguly@cognizant.com \
      --central-project cog01k24f1ea555zdv7ynzthxanz5 \
      --topic veriforgeops-telemetry-ingest \
      --sink-name veriforgeops-crossproject-sink \
      --log-name veriforgeops-crossproject

By default the sink uses a NARROW filter scoped to a dedicated log name so it
only routes telemetry you deliberately write — it will NOT siphon a producer
project's real audit logs. Override with --log-filter for broader capture
(e.g. the Vertex AI audit-log filter) once you understand the volume/cost.
"""

import argparse
import os
import subprocess
import sys


def gcloud(args, account=None):
    """Run a gcloud command and return (rc, stdout, stderr)."""
    env = dict(os.environ)
    # gcloud's bundled launcher can fail on Windows; pin a real interpreter if
    # CLOUDSDK_PYTHON is already set in the environment we inherit.
    cmd = ["gcloud"] + args
    if account:
        cmd += [f"--account={account}"]
    is_win = sys.platform == "win32"
    proc = subprocess.run(cmd, shell=is_win, text=True, capture_output=True, env=env)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def main():
    ap = argparse.ArgumentParser(description="Onboard a producer GCP project to the central Pub/Sub topic.")
    ap.add_argument("--producer-project", required=True, help="Project ID generating logs to onboard.")
    ap.add_argument("--producer-account", default=None, help="gcloud account with sink-admin on the producer project.")
    ap.add_argument("--central-project", default="cog01k24f1ea555zdv7ynzthxanz5", help="Central project that owns the topic.")
    ap.add_argument("--topic", default="veriforgeops-telemetry-ingest", help="Central Pub/Sub topic ID.")
    ap.add_argument("--sink-name", default="veriforgeops-crossproject-sink", help="Name of the sink to create in the producer project.")
    ap.add_argument("--log-name", default="veriforgeops-crossproject",
                    help="Dedicated log name the default (narrow) filter targets.")
    ap.add_argument("--log-filter", default=None,
                    help="Override the sink filter entirely (advanced — broad filters may route real prod logs).")
    args = ap.parse_args()

    destination = f"pubsub.googleapis.com/projects/{args.central_project}/topics/{args.topic}"
    log_filter = args.log_filter or f'logName="projects/{args.producer_project}/logs/{args.log_name}"'

    print("=" * 78)
    print(" VeriForge Ops — Cross-Project Sink Onboarding")
    print("=" * 78)
    print(f" Producer project : {args.producer_project}")
    print(f" Central topic    : {destination}")
    print(f" Sink name        : {args.sink_name}")
    print(f" Log filter       : {log_filter}")
    print("-" * 78)

    # Step 1: create (or update) the sink in the producer project.
    rc, out, err = gcloud([
        "logging", "sinks", "describe", args.sink_name,
        f"--project={args.producer_project}", "--format=value(name)",
    ], account=args.producer_account)

    if rc == 0:
        print(f"Sink '{args.sink_name}' already exists — updating filter/destination...")
        rc, out, err = gcloud([
            "logging", "sinks", "update", args.sink_name, destination,
            f"--log-filter={log_filter}", f"--project={args.producer_project}",
        ], account=args.producer_account)
    else:
        print(f"Creating sink '{args.sink_name}'...")
        rc, out, err = gcloud([
            "logging", "sinks", "create", args.sink_name, destination,
            f"--log-filter={log_filter}", f"--project={args.producer_project}",
        ], account=args.producer_account)

    if rc != 0:
        print("ERROR creating/updating sink:\n" + (err or out))
        sys.exit(1)
    print(out or "Sink configured.")

    # Step 2: read the writer identity.
    rc, writer, err = gcloud([
        "logging", "sinks", "describe", args.sink_name,
        f"--project={args.producer_project}", "--format=value(writerIdentity)",
    ], account=args.producer_account)
    if rc != 0 or not writer:
        print("ERROR reading writer identity:\n" + (err or out))
        sys.exit(1)

    print("\n" + "=" * 78)
    print(" ACTION REQUIRED — grant the sink writer identity publish rights")
    print("=" * 78)
    print(" The sink cannot deliver to the central topic until its writer identity")
    print(" is granted roles/pubsub.publisher on that topic. This step modifies")
    print(" IAM, so run it yourself with central-project credentials:\n")
    print(f"   Writer identity: {writer}\n")
    print("   gcloud pubsub topics add-iam-policy-binding \\")
    print(f"       {args.topic} \\")
    print(f"       --member='{writer}' \\")
    print("       --role='roles/pubsub.publisher' \\")
    print(f"       --project={args.central_project}\n")
    print(" Then write a test entry in the producer project and consume it centrally:")
    print(f"   gcloud logging write {args.log_name} \\")
    print('       \'{"cloud":"GCP","service":"Vertex AI","operation":"chat","associate_id":"tester","cost":0.01}\' \\')
    print(f"       --payload-type=json --project={args.producer_project}")
    print("=" * 78)


if __name__ == "__main__":
    main()
