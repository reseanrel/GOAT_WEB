#!/usr/bin/env python3

"""
Test script to verify that the template conditions work correctly
for handling photo_url values including 'None' string, NULL, and valid filenames.
"""

def test_template_condition(photo_url):
    """
    Simulate the template condition:
    {% if pet.photo_url and pet.photo_url != 'None' and pet.photo_url.strip() %}
    """
    # This simulates the Jinja2 template condition
    return bool(photo_url and photo_url != 'None' and (photo_url.strip() if photo_url else False))

def main():
    print("Testing template conditions for photo display...")

    # Test cases
    test_cases = [
        ('valid_filename.jpg', True, "Valid filename should show photo"),
        ('None', False, "String 'None' should NOT show photo"),
        ('', False, "Empty string should NOT show photo"),
        ('   ', False, "Whitespace should NOT show photo"),
        (None, False, "None (NULL) should NOT show photo"),
        ('another_valid_file.png', True, "Another valid filename should show photo"),
        ('file with spaces.jpg', True, "Filename with spaces should show photo"),
    ]

    print("\nTest Results:")
    print("-" * 60)

    all_passed = True

    for photo_url, expected_result, description in test_cases:
        actual_result = test_template_condition(photo_url)
        status = "PASS" if actual_result == expected_result else "FAIL"

        if actual_result != expected_result:
            all_passed = False

        print(f"{status} | {description}")
        print(f"     | Input: {repr(photo_url)}")
        print(f"     | Expected: {expected_result}, Got: {actual_result}")
        print(f"     | Condition: {photo_url} and {photo_url} != 'None' and {photo_url}.strip() = {actual_result}")
        print("-" * 60)

    print(f"\nOverall Result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

    # Test the specific case that was causing the issue
    print(f"\nSpecific Issue Test:")
    print(f"photo_url = 'None' (string)")
    print(f"Old condition (just 'if photo_url'): {bool('None')}")
    print(f"New condition (with != 'None' check): {test_template_condition('None')}")

    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)