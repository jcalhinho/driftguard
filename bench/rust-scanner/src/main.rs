// DriftGuard Rust scanner — benchmark against the Python engine.
//
// Usage: driftguard-rust <path> <rules.json>
// Prints a JSON summary: files scanned, findings, elapsed time.

use std::fs;
use std::time::Instant;

use regex::Regex;
use serde::Deserialize;
use walkdir::WalkDir;

#[derive(Deserialize)]
#[allow(dead_code)] // provider/title/severity reserved for the full report
struct Rule {
    id: String,
    provider: String,
    title: String,
    severity: String,
    patterns: Vec<String>,
}

#[derive(serde::Serialize)]
struct Finding<'a> {
    rule_id: &'a str,
    file: String,
    line: usize,
}

const SKIP_DIRS: &[&str] = &[
    ".git", "node_modules", ".venv", "venv", "env", "dist", "build", "out",
    "__pycache__", ".idea", ".vscode", ".driftguard", ".next", "vendor", "target",
];
const MAX_FILE_SIZE: u64 = 2 * 1024 * 1024;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: driftguard-rust <path> <rules.json>");
        std::process::exit(2);
    }
    let path = &args[1];
    let rules_json = fs::read_to_string(&args[2]).expect("cannot read rules file");
    let rules: Vec<Rule> = serde_json::from_str(&rules_json).expect("invalid rules JSON");
    let compiled: Vec<(Rule, Vec<Regex>)> = rules
        .into_iter()
        .map(|r| {
            let regexes = r
                .patterns
                .iter()
                .map(|p| Regex::new(p).expect("invalid regex"))
                .collect();
            (r, regexes)
        })
        .collect();

    let start = Instant::now();
    let mut findings: Vec<Finding> = Vec::new();
    let mut files_scanned = 0usize;

    let walker = WalkDir::new(path)
        .into_iter()
        .filter_entry(|e| {
            if e.file_type().is_dir() {
                let name = e.file_name().to_string_lossy();
                return !SKIP_DIRS.contains(&name.as_ref()) && !name.starts_with('.');
            }
            true
        })
        .filter_map(|e| e.ok());

    for entry in walker {
        if !entry.file_type().is_file() {
            continue;
        }
        let meta = match entry.metadata() {
            Ok(m) => m,
            Err(_) => continue,
        };
        if meta.len() == 0 || meta.len() > MAX_FILE_SIZE {
            continue;
        }
        let content = match fs::read(entry.path()) {
            Ok(c) => c,
            Err(_) => continue,
        };
        if content.iter().take(512).any(|&b| b == 0) {
            continue; // binary
        }
        let text = String::from_utf8_lossy(&content);
        files_scanned += 1;
        let rel = entry
            .path()
            .strip_prefix(path)
            .unwrap_or(entry.path())
            .to_string_lossy()
            .into_owned();

        for (rule, regexes) in &compiled {
            for re in regexes {
                for m in re.find_iter(&text) {
                    let line = text[..m.start()].matches('\n').count() + 1;
                    findings.push(Finding {
                        rule_id: &rule.id,
                        file: rel.clone(),
                        line,
                    });
                }
            }
        }
    }

    let elapsed = start.elapsed();
    println!(
        "{}",
        serde_json::json!({
            "files_scanned": files_scanned,
            "findings": findings.len(),
            "elapsed_ms": elapsed.as_millis(),
            "sample": findings.iter().take(5).map(|f| serde_json::json!({
                "rule_id": f.rule_id, "file": f.file, "line": f.line
            })).collect::<Vec<_>>(),
        })
    );
}
