#!/usr/bin/env python3
"""
capacity_calculator.py -- Estimate QPS, storage, and bandwidth from traffic assumptions.

Produces a markdown-formatted capacity estimation table suitable for inclusion
in a system design document. Includes recommendations for database type based
on workload characteristics.
"""

import argparse
import math
import sys


def format_bytes(num_bytes):
    """Format bytes into a human-readable string."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 ** 2:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 ** 3:
        return f"{num_bytes / 1024 ** 2:.1f} MB"
    elif num_bytes < 1024 ** 4:
        return f"{num_bytes / 1024 ** 3:.1f} GB"
    else:
        return f"{num_bytes / 1024 ** 4:.1f} TB"


def format_qps(qps):
    """Format QPS with appropriate precision."""
    if qps < 1:
        return f"{qps:.2f}"
    elif qps < 100:
        return f"{qps:.1f}"
    elif qps < 10000:
        return f"{qps:,.0f}"
    else:
        return f"{qps:,.0f}"


def recommend_db(write_qps, read_qps, read_write_ratio, record_bytes, storage_1yr):
    """Recommend a database type based on workload characteristics."""
    recommendations = []

    total_qps = write_qps + read_qps
    storage_1yr_gb = storage_1yr / (1024 ** 3)

    if read_write_ratio >= 10 and total_qps < 10000:
        recommendations.append(
            ("PostgreSQL / MySQL", "Read-heavy workload with moderate QPS -- relational DB with read replicas works well")
        )
    if write_qps > 5000:
        recommendations.append(
            ("Cassandra / ScyllaDB", "High write throughput needs a write-optimized distributed store")
        )
    if read_write_ratio >= 50:
        recommendations.append(
            ("Redis (cache layer)", "Very high read-to-write ratio benefits from a caching layer in front of the primary store")
        )
    if record_bytes < 1024 and total_qps > 10000:
        recommendations.append(
            ("DynamoDB / Redis", "Small records at high QPS suit key-value stores")
        )
    if storage_1yr_gb > 1000:
        recommendations.append(
            ("S3 + metadata DB", "Large storage footprint -- consider object storage for blobs with a metadata database for indexing")
        )
    if total_qps < 1000 and storage_1yr_gb < 100:
        recommendations.append(
            ("PostgreSQL", "Moderate load and storage -- a single PostgreSQL instance with connection pooling is simplest")
        )

    if not recommendations:
        recommendations.append(
            ("PostgreSQL (default)", "Workload does not have extreme characteristics -- start simple with a relational database")
        )

    return recommendations


def calculate(users, writes_per_user, read_write_ratio, record_bytes):
    """Run all capacity calculations and return a structured result."""
    # Monthly writes
    monthly_writes = users * writes_per_user
    monthly_reads = monthly_writes * read_write_ratio
    monthly_total = monthly_writes + monthly_reads

    # Seconds in a month (30 days)
    seconds_per_month = 30 * 24 * 3600

    # Average QPS
    write_qps = monthly_writes / seconds_per_month
    read_qps = monthly_reads / seconds_per_month
    total_qps = write_qps + read_qps

    # Peak QPS (assume 3x average for daily peaks)
    peak_write_qps = write_qps * 3
    peak_read_qps = read_qps * 3
    peak_total_qps = total_qps * 3

    # Storage calculations (cumulative, no deletions assumed)
    monthly_storage = monthly_writes * record_bytes
    storage_1yr = monthly_storage * 12
    storage_3yr = monthly_storage * 36
    storage_5yr = monthly_storage * 60

    # Bandwidth (average)
    write_bandwidth = write_qps * record_bytes  # bytes per second
    read_bandwidth = read_qps * record_bytes

    # DB recommendations
    db_recs = recommend_db(write_qps, read_qps, read_write_ratio, record_bytes, storage_1yr)

    return {
        "users": users,
        "writes_per_user": writes_per_user,
        "read_write_ratio": read_write_ratio,
        "record_bytes": record_bytes,
        "monthly_writes": monthly_writes,
        "monthly_reads": monthly_reads,
        "write_qps": write_qps,
        "read_qps": read_qps,
        "total_qps": total_qps,
        "peak_write_qps": peak_write_qps,
        "peak_read_qps": peak_read_qps,
        "peak_total_qps": peak_total_qps,
        "storage_1yr": storage_1yr,
        "storage_3yr": storage_3yr,
        "storage_5yr": storage_5yr,
        "write_bandwidth": write_bandwidth,
        "read_bandwidth": read_bandwidth,
        "db_recommendations": db_recs,
    }


def format_output(results):
    """Format results as markdown tables."""
    lines = []

    lines.append("## Capacity Estimation")
    lines.append("")
    lines.append("### Assumptions")
    lines.append("")
    lines.append("| Parameter | Value |")
    lines.append("|---|---|")
    lines.append(f"| Monthly Active Users | {results['users']:,} |")
    lines.append(f"| Writes per user per month | {results['writes_per_user']:,} |")
    lines.append(f"| Read:Write ratio | {results['read_write_ratio']}:1 |")
    lines.append(f"| Avg record size | {format_bytes(results['record_bytes'])} |")
    lines.append("")

    lines.append("### Traffic")
    lines.append("")
    lines.append("| Metric | Average | Peak (3x) |")
    lines.append("|---|---|---|")
    lines.append(f"| Write QPS | {format_qps(results['write_qps'])} | {format_qps(results['peak_write_qps'])} |")
    lines.append(f"| Read QPS | {format_qps(results['read_qps'])} | {format_qps(results['peak_read_qps'])} |")
    lines.append(f"| Total QPS | {format_qps(results['total_qps'])} | {format_qps(results['peak_total_qps'])} |")
    lines.append("")

    lines.append("### Storage (cumulative, no deletions)")
    lines.append("")
    lines.append("| Timeframe | Storage |")
    lines.append("|---|---|")
    lines.append(f"| 1 year | {format_bytes(results['storage_1yr'])} |")
    lines.append(f"| 3 years | {format_bytes(results['storage_3yr'])} |")
    lines.append(f"| 5 years | {format_bytes(results['storage_5yr'])} |")
    lines.append("")

    lines.append("### Bandwidth (average)")
    lines.append("")
    lines.append("| Direction | Throughput |")
    lines.append("|---|---|")
    lines.append(f"| Write (inbound) | {format_bytes(results['write_bandwidth'])}/s |")
    lines.append(f"| Read (outbound) | {format_bytes(results['read_bandwidth'])}/s |")
    lines.append(f"| Total | {format_bytes(results['write_bandwidth'] + results['read_bandwidth'])}/s |")
    lines.append("")

    lines.append("### Database Recommendation")
    lines.append("")
    for db_name, reason in results["db_recommendations"]:
        lines.append(f"- **{db_name}**: {reason}")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Calculate QPS, storage, and bandwidth from traffic assumptions.",
        epilog="Output is formatted as markdown tables for inclusion in design documents.",
    )
    parser.add_argument(
        "--users",
        type=int,
        required=True,
        help="Monthly active users (MAU)",
    )
    parser.add_argument(
        "--writes-per-user",
        type=int,
        required=True,
        help="Write operations per user per month",
    )
    parser.add_argument(
        "--read-write-ratio",
        type=float,
        default=10,
        help="Read-to-write ratio (default: 10, meaning 10 reads per write)",
    )
    parser.add_argument(
        "--record-bytes",
        type=int,
        default=500,
        help="Average record size in bytes (default: 500)",
    )

    args = parser.parse_args()

    if args.users <= 0:
        print("Error: --users must be a positive integer.", file=sys.stderr)
        sys.exit(1)
    if args.writes_per_user <= 0:
        print("Error: --writes-per-user must be a positive integer.", file=sys.stderr)
        sys.exit(1)
    if args.read_write_ratio < 0:
        print("Error: --read-write-ratio must be non-negative.", file=sys.stderr)
        sys.exit(1)
    if args.record_bytes <= 0:
        print("Error: --record-bytes must be a positive integer.", file=sys.stderr)
        sys.exit(1)

    results = calculate(args.users, args.writes_per_user, args.read_write_ratio, args.record_bytes)
    print(format_output(results))


if __name__ == "__main__":
    main()
