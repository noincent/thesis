#!/bin/bash
# CHESS+ MySQL Migration Test Suite Runner

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  CHESS+ MySQL Migration Test Suite${NC}"
echo -e "${BLUE}==================================================${NC}"

# Check if we should initialize schema
INIT_FLAG=""
if [[ "$1" == "--init" ]]; then
  echo -e "${YELLOW}Running with schema initialization${NC}"
  INIT_FLAG="--init-schema"
fi

# Function to run a test and check its exit code
run_test() {
  local test_script=$1
  local test_name=$2
  local test_args=$3
  
  echo -e "\n${BLUE}Running $test_name...${NC}"
  python3 $test_script $test_args
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}$test_name: PASSED${NC}"
    return 0
  else
    echo -e "${RED}$test_name: FAILED${NC}"
    return 1
  fi
}

# Track overall success
OVERALL_SUCCESS=0

# Step 1: Test basic MySQL connection
run_test "test_mysql_connection.py" "MySQL Connection Test" "$INIT_FLAG"
if [ $? -ne 0 ]; then
  echo -e "\n${RED}Connection test failed. Please fix connection issues before continuing.${NC}"
  echo -e "${YELLOW}Check your .env file and make sure MySQL server is running.${NC}"
  exit 1
fi

# Step 2: Test MySQL functionality (LSH, Vector Storage, Transactions)
run_test "test_mysql_functionality.py" "MySQL Functionality Test" "--test all"
if [ $? -ne 0 ]; then
  OVERALL_SUCCESS=1
fi

# Step 3: Test integration with preprocessing modules
run_test "test_mysql_integration.py" "MySQL Integration Test" "$INIT_FLAG"
if [ $? -ne 0 ]; then
  OVERALL_SUCCESS=1
fi

# Step 4: Test end-to-end workflow
run_test "test_mysql_integration.py" "End-to-End Workflow Test" "$INIT_FLAG --test workflow"
if [ $? -ne 0 ]; then
  OVERALL_SUCCESS=1
fi

# Final summary
echo -e "\n${BLUE}==================================================${NC}"

if [ $OVERALL_SUCCESS -eq 0 ]; then
  echo -e "${GREEN}All tests passed successfully!${NC}"
  echo -e "${GREEN}The MySQL migration is working correctly.${NC}"
else
  echo -e "${RED}Some tests failed. Please review the output above for details.${NC}"
  echo -e "${YELLOW}The MySQL migration may require additional work.${NC}"
fi

echo -e "${BLUE}==================================================${NC}"

exit $OVERALL_SUCCESS