#!/usr/bin/env python3
"""
Validate template JSON theo schema chuẩn.

Sử dụng:
    python scripts/validate_template.py templates/samples/small.json
    python scripts/validate_template.py --all  # Validate tất cả samples

Yêu cầu:
    pip install jsonschema
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("Lỗi: Cần cài đặt jsonschema")
    print("Chạy: pip install jsonschema")
    sys.exit(1)


def load_schema() -> dict:
    """Load JSON Schema từ file."""
    schema_path = Path(__file__).parent.parent / "schemas" / "template.json"
    if not schema_path.exists():
        print(f"Lỗi: Không tìm thấy schema tại {schema_path}")
        sys.exit(1)
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def validate_template(template_path: str, verbose: bool = False) -> list[dict]:
    """
    Validate template JSON theo schema.

    Returns:
        Danh sách lỗi (rỗng nếu hợp lệ)
    """
    schema = load_schema()
    validator = Draft202012Validator(schema)

    with open(template_path, encoding="utf-8") as f:
        try:
            template = json.load(f)
        except json.JSONDecodeError as e:
            return [{"path": "", "message": f"JSON không hợp lệ: {e}"}]

    errors = []
    for error in validator.iter_errors(template):
        error_info = {
            "path": "/".join(str(p) for p in error.absolute_path) or "(root)",
            "message": error.message
        }
        errors.append(error_info)
        if verbose:
            print(f"  - [{error_info['path']}] {error_info['message']}")

    return errors


def validate_all_samples(verbose: bool = False) -> bool:
    """Validate tất cả samples trong templates/samples/."""
    samples_dir = Path(__file__).parent.parent / "templates" / "samples"
    all_valid = True

    for sample_file in sorted(samples_dir.glob("*.json")):
        print(f"\nValidating: {sample_file.name}")
        errors = validate_template(str(sample_file), verbose=verbose)

        if errors:
            print(f"  INVALID - {len(errors)} lỗi")
            all_valid = False
            if not verbose:
                for err in errors[:3]:  # Hiển thị tối đa 3 lỗi
                    print(f"    - [{err['path']}] {err['message']}")
                if len(errors) > 3:
                    print(f"    ... và {len(errors) - 3} lỗi khác")
        else:
            print("  VALID")

    return all_valid


def main():
    parser = argparse.ArgumentParser(
        description="Validate template JSON theo schema chuẩn"
    )
    parser.add_argument(
        "template",
        nargs="?",
        help="Đường dẫn file template JSON"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate tất cả samples trong templates/samples/"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Hiển thị chi tiết lỗi"
    )

    args = parser.parse_args()

    if args.all:
        success = validate_all_samples(verbose=args.verbose)
        sys.exit(0 if success else 1)

    if not args.template:
        parser.print_help()
        sys.exit(1)

    template_path = Path(args.template)
    if not template_path.exists():
        print(f"Lỗi: Không tìm thấy file {template_path}")
        sys.exit(1)

    print(f"Validating: {template_path}")
    errors = validate_template(str(template_path), verbose=args.verbose)

    if errors:
        print(f"INVALID - {len(errors)} lỗi")
        if not args.verbose:
            for err in errors:
                print(f"  - [{err['path']}] {err['message']}")
        sys.exit(1)
    else:
        print("VALID")
        sys.exit(0)


if __name__ == "__main__":
    main()
