#!/bin/bash

# Colors and emojis for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
CHECK_EMOJI="✅"
CROSS_EMOJI="❌"
CLOCK_EMOJI="🕒"

# File names (can be easily changed)
REFUSED_RULES_FILE="ruff-refused-rules.txt"
CHECK_LATER_FILE="ruff-check-later.txt"

# Function to get rule information
get_rule_info() {
    local rule=$1
    ruff rule "$rule" --output-format json | jq -r '[.code, .name, .summary] | @tsv'
}

# Function to display rule information
display_rule_info() {
    local rule=$1
    local info
    info=$(get_rule_info "$rule")
    IFS=$'\t' read -r code name summary <<< "$info"
    echo -e "${BLUE}Rule: $code - $name${NC}"
    echo -e "${YELLOW}Summary: $summary${NC}"
}

# Function to check if a rule is refused
is_rule_refused() {
    local rule=$1
    grep -q "^$rule$" "$REFUSED_RULES_FILE" 2>/dev/null
}

# Function to display diff and prompt for action
process_rule() {
    local rule=$1
    echo -e "\n${GREEN}Processing rule: $rule${NC}"

    echo -e "\n${YELLOW}Diff:${NC}"
    ruff check --select "$rule" --diff

    while true; do
        display_rule_info "$rule"

        echo -e "\n${GREEN}Choose an action:${NC}"
        echo -e "a) ${CHECK_EMOJI} Accept fixes"
        echo -e "r) ${CROSS_EMOJI} Refuse fixes"
        echo -e "l) ${CLOCK_EMOJI} Mark for later"
        read -rp "Enter your choice (a/r/l): " choice

        case $choice in
            a)
                ruff check --select "$rule" --fix
                echo -e "${GREEN}${CHECK_EMOJI} Fixes applied for $rule${NC}"
                break
                ;;
            r)
                echo "$rule" >> "$REFUSED_RULES_FILE"
                echo -e "${RED}${CROSS_EMOJI} Rule $rule added to $REFUSED_RULES_FILE${NC}"
                break
                ;;
            l)
                echo "$rule" >> "$CHECK_LATER_FILE"
                echo -e "${YELLOW}${CLOCK_EMOJI} Rule $rule added to $CHECK_LATER_FILE${NC}"
                break
                ;;
            *)
                echo -e "${RED}Invalid choice. Please enter a, b, or c.${NC}"
                ;;
        esac
    done
}

# Main function
main() {
    local fixable_rules
    fixable_rules=$(ruff check --output-format json |
        jq -r '[.[] | select(.fix.applicability == "safe")] | .[].code' |
        sort | uniq -c | sort -rn | cut -c 9-
    )
    for rule in $fixable_rules; do
        if is_rule_refused "$rule"; then
            echo -e "${YELLOW}Skipping refused rule: $rule${NC}"
        else
            process_rule "$rule"
        fi
    done

    echo -e "\n${GREEN}All rules processed!${NC}"
}

# Run the main function
main
