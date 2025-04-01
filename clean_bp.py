import re
import sys
import os

def remove_duplicate_bp_modules(input_filename, output_filename):
    """
    Reads an Android.bp file, removes duplicate module definitions based on the 'name' property,
    and writes the cleaned content to a new file.
    """
    seen_names = set()
    current_block_lines = []
    current_block_name = None
    in_block = False
    brace_level = 0

    # Regex patterns
    # Matches module type { (e.g., cc_prebuilt_library_shared { ) potentially with comments
    block_start_pattern = re.compile(r'^\s*(\w+)\s*{\s*(#.*)?$')
    # Extracts name: "..." , allowing for optional comma and comments
    name_pattern = re.compile(r'^\s*name:\s*"([^"]+)"\s*,?\s*(#.*)?$')
    # Matches lines containing braces to track block level
    open_brace_pattern = re.compile(r'{')
    close_brace_pattern = re.compile(r'}')

    print(f"Processing {input_filename}...")
    try:
        with open(input_filename, 'r', encoding='utf-8') as infile, \
             open(output_filename, 'w', encoding='utf-8') as outfile:

            for line_num, line in enumerate(infile, 1):
                stripped_line = line.strip()

                if not in_block:
                    # Check if a new block starts
                    match_start = block_start_pattern.match(stripped_line)
                    if match_start and stripped_line.endswith('{'): # Basic check for start
                        in_block = True
                        current_block_lines = [line]
                        current_block_name = None
                        brace_level = 1 # Started with one opening brace
                        # Check if name is on the same line (less common)
                        match_name = name_pattern.match(stripped_line)
                        if match_name:
                             current_block_name = match_name.group(1)
                    else:
                        # Write lines outside blocks directly
                        outfile.write(line)
                else: # We are inside a block
                    current_block_lines.append(line)

                    # Track brace level robustly
                    brace_level += len(open_brace_pattern.findall(line))
                    brace_level -= len(close_brace_pattern.findall(line))

                    # Check for the name property within the block
                    if current_block_name is None: # Only find the first name
                        match_name = name_pattern.match(stripped_line)
                        if match_name:
                            current_block_name = match_name.group(1)

                    # Check if the block ends (brace level returns to 0)
                    if brace_level <= 0:
                        in_block = False
                        if current_block_name:
                            if current_block_name not in seen_names:
                                seen_names.add(current_block_name)
                                # Write the entire block
                                for block_line in current_block_lines:
                                    outfile.write(block_line)
                                # print(f"Kept module: {current_block_name}") # Debugging
                            else:
                                # print(f"Skipped duplicate module: {current_block_name}") # Debugging
                                pass # Duplicate name, discard the block
                        else:
                            # Block ended without a name found. This could be a comment block,
                            # a structure without a name, or an error in parsing.
                            # To be safe, write it out. Modules needing deduplication should have names.
                            # print(f"Warning: Block ending at line {line_num} had no 'name' property found. Writing it.")
                            for block_line in current_block_lines:
                                outfile.write(block_line)

                        # Reset for the next potential block
                        current_block_lines = []
                        current_block_name = None
                        brace_level = 0 # Ensure reset

            # Handle case where file ends while still inside a block (malformed bp file?)
            if in_block:
                print(f"Warning: File {input_filename} ended unexpectedly while inside a block (brace level {brace_level}).", file=sys.stderr)
                print(f"Warning: Writing potentially incomplete block starting with: {current_block_lines[0].strip()}", file=sys.stderr)
                # Decide whether to write the incomplete block. Let's write it.
                if current_block_name and current_block_name not in seen_names:
                     print(f"Warning: Writing incomplete block for module {current_block_name} as it wasn't seen before.", file=sys.stderr)
                     for block_line in current_block_lines:
                         outfile.write(block_line)
                elif not current_block_name:
                     print(f"Warning: Writing incomplete block with no name found.", file=sys.stderr)
                     for block_line in current_block_lines:
                         outfile.write(block_line)


        print(f"Finished processing. Found {len(seen_names)} unique named modules.")
        print(f"Cleaned output written to {output_filename}")
        print(f"\nPlease review {output_filename} carefully before replacing {input_filename}.")
        print(f"You can compare the files using: diff {input_filename} {output_filename}")
        print(f"Or check the line count difference: wc -l {input_filename} {output_filename}")

    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    input_bp = "Android.bp"
    output_bp = "Android.bp.cleaned"

    # Basic check if input file exists
    if not os.path.exists(input_bp):
         print(f"Error: Input file '{input_bp}' does not exist in the current directory.", file=sys.stderr)
         sys.exit(1)

    remove_duplicate_bp_modules(input_bp, output_bp)
