from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.tsx")
text = p.read_text(encoding="utf-8")

def wire(old, new, label):
    global text
    count = text.count(old)
    assert count >= 1, f"{label}: not found"
    text = text.replace(old, new)
    print(f"{label}: wired {count} site(s)")

# Identity decisions (queue page) — success + error.
wire(
    "      setIdentityMessageIsError(false);\n      setIdentityMessage(`${done} with receipt ${receipt.decision_id}${linked}`);",
    "      setIdentityMessageIsError(false);\n      setIdentityMessage(`${done} with receipt ${receipt.decision_id}${linked}`);\n      toast.push(\"success\", `${done} with receipt ${receipt.decision_id}${linked}`);",
    "identity success",
)
wire(
    "      setIdentityMessageIsError(true);\n      setIdentityMessage(error instanceof Error && error.message ? error.message : \"Identity decision failed\");",
    "      setIdentityMessageIsError(true);\n      setIdentityMessage(error instanceof Error && error.message ? error.message : \"Identity decision failed\");\n      toast.push(\"error\", error instanceof Error && error.message ? error.message : \"Identity decision failed\");",
    "identity error",
)

# Entity profile save — success + error.
wire(
    "      setEntityProfileMessageIsError(false);\n      setEntityProfileMessage(`Saved with receipt ${receipt.receipt_id}`",
    "      setEntityProfileMessageIsError(false);\n      setEntityProfileMessage(`Saved with receipt ${receipt.receipt_id}`",
    "profile save (message built inline; toast appended below)",
)
# Append the toast to the end of the profile-save message statement.
old = "         receipt.alias_sync.skipped_conflicting.length ? ` skipped (owned by another identity): ${receipt.alias_sync.skipped_conflicting.join(\", \")}` : \"\"].filter(Boolean).join(\";\") : \"\"));"
new = old + "\n      toast.push(\"success\", `Profile saved with receipt ${receipt.receipt_id.slice(0, 8)}`);"
assert old in text, "profile save tail"
text = text.replace(old, new, 1)

wire(
    "      setEntityProfileMessageIsError(true);\n      setEntityProfileMessage(error instanceof Error ? error.message : \"Profile could not be saved\");",
    "      setEntityProfileMessageIsError(true);\n      setEntityProfileMessage(error instanceof Error ? error.message : \"Profile could not be saved\");\n      toast.push(\"error\", error instanceof Error ? error.message : \"Profile could not be saved\");",
    "profile save error",
)

# Kind correction — success + error.
wire(
    "      setEntityProfileMessageIsError(false);\n      setEntityProfileMessage(`Kind corrected to ${display(kind)} — proposal ${proposal.proposal_id.slice(0, 8)} applied`);",
    "      setEntityProfileMessageIsError(false);\n      setEntityProfileMessage(`Kind corrected to ${display(kind)} — proposal ${proposal.proposal_id.slice(0, 8)} applied`);\n      toast.push(\"success\", `Kind corrected to ${display(kind)} — proposal ${proposal.proposal_id.slice(0, 8)} applied`);",
    "kind success",
)
wire(
    "      setEntityProfileMessageIsError(true);\n      setEntityProfileMessage(error instanceof Error ? error.message : \"Kind correction failed\");",
    "      setEntityProfileMessageIsError(true);\n      setEntityProfileMessage(error instanceof Error ? error.message : \"Kind correction failed\");\n      toast.push(\"error\", error instanceof Error ? error.message : \"Kind correction failed\");",
    "kind error",
)

# Membership add/remove + role assignment (App-level handlers).
wire(
    "      setEntityProfileMessageIsError(false);\n      setEntityProfileMessage(`Added ${member.canonical_name} to ${selectedEntry.canonical_name} with receipt ${receipt.decision_id.slice(0, 8)}`);",
    "      setEntityProfileMessageIsError(false);\n      setEntityProfileMessage(`Added ${member.canonical_name} to ${selectedEntry.canonical_name} with receipt ${receipt.decision_id.slice(0, 8)}`);\n      toast.push(\"success\", `Added ${member.canonical_name} to ${selectedEntry.canonical_name}`);",
    "member add success",
)
wire(
    "      setEntityProfileMessageIsError(true);\n      setEntityProfileMessage(error instanceof Error && error.message ? error.message : \"Membership decision failed\");",
    "      setEntityProfileMessageIsError(true);\n      setEntityProfileMessage(error instanceof Error && error.message ? error.message : \"Membership decision failed\");\n      toast.push(\"error\", error instanceof Error && error.message ? error.message : \"Membership decision failed\");",
    "membership error (2 sites)",
)
wire(
    "      setEntityProfileMessageIsError(false);\n      setEntityProfileMessage(`Removed ${member.name} from ${selectedEntry.canonical_name} with receipt ${receipt.decision_id.slice(0, 8)}`);",
    "      setEntityProfileMessageIsError(false);\n      setEntityProfileMessage(`Removed ${member.name} from ${selectedEntry.canonical_name} with receipt ${receipt.decision_id.slice(0, 8)}`);\n      toast.push(\"success\", `Removed ${member.name} from ${selectedEntry.canonical_name}`);",
    "member remove success",
)
wire(
    "      setEntityProfileMessageIsError(false);\n      setEntityProfileMessage(roleName\n        ? `Seated ${member.name} as ${roleName}${isLeadership ? \" ★\" : \"\"} in ${selectedEntry.canonical_name}`\n        : `Cleared ${member.name}'s role in ${selectedEntry.canonical_name}`);",
    "      setEntityProfileMessageIsError(false);\n      setEntityProfileMessage(roleName\n        ? `Seated ${member.name} as ${roleName}${isLeadership ? \" ★\" : \"\"} in ${selectedEntry.canonical_name}`\n        : `Cleared ${member.name}'s role in ${selectedEntry.canonical_name}`);\n      toast.push(\"success\", roleName\n        ? `Seated ${member.name} as ${roleName}${isLeadership ? \" ★\" : \"\"} in ${selectedEntry.canonical_name}`\n        : `Cleared ${member.name}'s role in ${selectedEntry.canonical_name}`);",
    "role assign success",
)
wire(
    "      setEntityProfileMessageIsError(true);\n      setEntityProfileMessage(error instanceof Error && error.message ? error.message : \"Role decision failed\");",
    "      setEntityProfileMessageIsError(true);\n      setEntityProfileMessage(error instanceof Error && error.message ? error.message : \"Role decision failed\");\n      toast.push(\"error\", error instanceof Error && error.message ? error.message : \"Role decision failed\");",
    "role assign error",
)

# Roles page decide — success + error (module scope has toast imported).
wire(
    "      setMessageIsError(false);\n      setMessage(done);",
    "      setMessageIsError(false);\n      setMessage(done);\n      toast.push(\"success\", done);",
    "roles page success",
)
wire(
    "      setMessageIsError(true);\n      setMessage(error instanceof Error && error.message ? error.message : \"Role decision failed\");",
    "      setMessageIsError(true);\n      setMessage(error instanceof Error && error.message ? error.message : \"Role decision failed\");\n      toast.push(\"error\", error instanceof Error && error.message ? error.message : \"Role decision failed\");",
    "roles page error",
)

# PC profile save — success + error.
wire(
    "      setPCMessage(`Saved with receipt ${receipt.receipt_id}${syncCopy}`);",
    "      setPCMessage(`Saved with receipt ${receipt.receipt_id}${syncCopy}`);\n      toast.push(\"success\", `PC profile saved with receipt ${receipt.receipt_id.slice(0, 8)}`);",
    "pc save success",
)
wire(
    "    } catch (error) { setPCMessage(error instanceof Error ? error.message : \"PC profile could not be saved\"); }",
    "    } catch (error) { setPCMessage(error instanceof Error ? error.message : \"PC profile could not be saved\"); toast.push(\"error\", error instanceof Error ? error.message : \"PC profile could not be saved\"); }",
    "pc save error",
)

# Claim correction — success + error.
wire(
    "      setClaimEditMessage(`Claim corrected with receipt ${receipt.receipt_id}`);",
    "      setClaimEditMessage(`Claim corrected with receipt ${receipt.receipt_id}`);\n      toast.push(\"success\", `Claim corrected with receipt ${receipt.receipt_id.slice(0, 8)}`);",
    "claim success",
)
wire(
    "    } catch (error) { setClaimEditMessage(error instanceof Error ? error.message : \"Claim correction failed\"); }",
    "    } catch (error) { setClaimEditMessage(error instanceof Error ? error.message : \"Claim correction failed\"); toast.push(\"error\", error instanceof Error ? error.message : \"Claim correction failed\"); }",
    "claim error",
)

# Session capture failure (the terminal one on submit).
wire(
    "      setSessionCaptureError(error instanceof Error ? error.message : \"Session note could not be captured\");",
    "      setSessionCaptureError(error instanceof Error ? error.message : \"Session note could not be captured\");\n      toast.push(\"error\", error instanceof Error ? error.message : \"Session note could not be captured\");",
    "capture error",
)

p.write_text(text, encoding="utf-8")
print("wiring complete")
