#!/bin/bash

# working directory needs to be the same as the script
cd "$(dirname "$0")"

# for each test there is a folder at "../../examples" with the same name
test_names=$(ls ../../examples)

count_pass=0
count_fail=0

# for each test we call 'python3.11 ./test_one.py <test_name>'
for test_name in $test_names ; do

    # get the absolute path of the test
    test_path=$(realpath ../../examples/$test_name)

    # ensure the test is a directory
    if [ ! -d $test_path ]; then
        echo "Ignoring file '$test_name'."
        continue
    fi

    echo "Running test: $test_name"

    # get the exit code of the test into 'exit_code'
    python3.8 ./test_one.py $test_path
    exit_code=$?

    # print a message based on the exit code and increment the corresponding counter
    if [ $exit_code -eq 0 ]; then
        echo "└ PASS for '${test_name}'."
        count_pass=$((count_pass+1))
    else
        echo "└ FAIL for '${test_name}'."
        count_fail=$((count_fail+1))
    fi

done

# it is good to inform the user about the total counts
echo "== TOTAL COUNTS =="
echo "- Tests passed: $count_pass"
echo "- Tests failed: $count_fail"

# if one fails, we consider the whole test as failed
if [ $count_fail -ne 0 ]; then
    exit 1
fi
exit 0
