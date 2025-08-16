#!/bin/bash

# Check for required command line arguments
if [ $# -lt 2 ]; then
  echo "Usage: $0 <graphql_endpoint> <plan_id1,plan_id2,...>"
  echo "Example: $0 http://localhost:8000/v1/graphql/ plan1,plan2,plan3"
  exit 1
fi

GRAPHQL_ENDPOINT="$1"
PLAN_IDS="$2"

if [ -z "$GRAPHQL_ENDPOINT" ]; then
  echo "ERROR: GraphQL endpoint must be provided"
  exit 1
fi

if [ -z "$PLAN_IDS" ]; then
  echo "ERROR: Plan IDs must be provided"
  exit 1
fi

execute_mutation() {
  local query="$1"

  local escaped_query=$(echo "$query" | sed 's/"/\\"/g')

  local json_payload="{\"query\": \"$escaped_query\"}"

  local response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$json_payload" \
    $GRAPHQL_ENDPOINT)

  if ! echo "$response" | jq . > /dev/null 2>&1; then
    echo "ERROR: Response is not valid JSON"
    echo "Raw response: $response"
    return 1
  fi

  if echo "$response" | jq -e '.errors' > /dev/null; then
    echo "ERROR: GraphQL request failed:"
    echo "$response" | jq '.errors'
    return 1
  fi

  if ! echo "$response" | jq -e '.data' > /dev/null; then
    echo "ERROR: No data in response"
    echo "Response: $response"
    return 1
  fi

  echo "$response"
}

extract_field() {
  local response="$1"
  local field="$2"

  local value=$(echo "$response" | jq -r "$field")

  if [ "$value" = "null" ]; then
    echo "ERROR: Extracted value is null for field $field"
    return 1
  fi

  echo "$value"
}

echo "=== Starting Test Data Population ==="
echo "GraphQL Endpoint: $GRAPHQL_ENDPOINT"
echo "Plan IDs: $PLAN_IDS"

for PLAN_ID in $(echo $PLAN_IDS | sed -e 's/,/ /g'); do
  echo "=== Processing Plan ID: $PLAN_ID ==="

  # 1. Create an organization
  echo "Creating organization for plan $PLAN_ID..."
  ORG_MUTATION='mutation { testMode { createOrganization(name: "Test Organization") { uuid } } }'
  ORG_RESPONSE=$(execute_mutation "$ORG_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create organization. Continuing to next plan."
    continue
  fi

  ORG_UUID=$(extract_field "$ORG_RESPONSE" '.data.testMode.createOrganization.uuid')
  if [ $? -ne 0 ]; then
    echo "Failed to extract organization UUID. Continuing to next plan."
    continue
  fi
  echo "Created organization with UUID: $ORG_UUID"

  # 2. Create a plan
  echo "Creating plan $PLAN_ID..."
  PLAN_MUTATION="mutation { testMode { createPlan(identifier: \"$PLAN_ID\", name: \"$PLAN_ID Plan\", organizationUuid: \"$ORG_UUID\") { id } } }"
  PLAN_RESPONSE=$(execute_mutation "$PLAN_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create plan $PLAN_ID. Continuing to next plan."
    continue
  fi
  PLAN_ID_NUM=$(extract_field "$PLAN_RESPONSE" '.data.testMode.createPlan.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract plan ID. Continuing to next plan."
    continue
  fi
  echo "Created plan with ID: $PLAN_ID_NUM"

  # 3. Create plan root page
  echo "Creating plan root page..."
  ROOT_PAGE_MUTATION="mutation { testMode { createPlanRootPage(planIdentifier: \"$PLAN_ID\", title: \"$PLAN_ID Root\") { id } } }"
  ROOT_PAGE_RESPONSE=$(execute_mutation "$ROOT_PAGE_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create plan root page. Exiting."
    exit 1
  fi
  ROOT_PAGE_ID=$(extract_field "$ROOT_PAGE_RESPONSE" '.data.testMode.createPlanRootPage.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract root page ID. Exiting."
    exit 1
  fi
  echo "Created plan root page with ID: $ROOT_PAGE_ID"

  # 4. Create action list page
  echo "Creating action list page..."
  ACTION_LIST_MUTATION="mutation { testMode { createActionListPage(planIdentifier: \"$PLAN_ID\", title: \"Actions\") { id } } }"
  ACTION_LIST_RESPONSE=$(execute_mutation "$ACTION_LIST_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create action list page. Exiting."
    exit 1
  fi
  ACTION_LIST_ID=$(extract_field "$ACTION_LIST_RESPONSE" '.data.testMode.createActionListPage.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract action list page ID. Exiting."
    exit 1
  fi
  echo "Created action list page with ID: $ACTION_LIST_ID"

  # 5. Create indicator list page
  echo "Creating indicator list page..."
  INDICATOR_LIST_MUTATION="mutation { testMode { createIndicatorListPage(planIdentifier: \"$PLAN_ID\", title: \"Indicators\") { id } } }"
  INDICATOR_LIST_RESPONSE=$(execute_mutation "$INDICATOR_LIST_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create indicator list page. Exiting."
    exit 1
  fi
  INDICATOR_LIST_ID=$(extract_field "$INDICATOR_LIST_RESPONSE" '.data.testMode.createIndicatorListPage.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract indicator list page ID. Exiting."
    exit 1
  fi
  echo "Created indicator list page with ID: $INDICATOR_LIST_ID"

  # 6. Create empty page
  echo "Creating empty page..."
  EMPTY_PAGE_MUTATION="mutation { testMode { createEmptyPage(planIdentifier: \"$PLAN_ID\", title: \"Empty Page\") { id } } }"
  EMPTY_PAGE_RESPONSE=$(execute_mutation "$EMPTY_PAGE_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create empty page. Exiting."
    exit 1
  fi
  EMPTY_PAGE_ID=$(extract_field "$EMPTY_PAGE_RESPONSE" '.data.testMode.createEmptyPage.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract empty page ID. Exiting."
    exit 1
  fi
  echo "Created empty page with ID: $EMPTY_PAGE_ID"

  # 7. Create static page under empty page
  echo "Creating static page under empty page..."
  STATIC_PAGE_MUTATION="mutation { testMode { createStaticPage(planIdentifier: \"$PLAN_ID\", title: \"Static Page\", parentId: $EMPTY_PAGE_ID) { id } } }"
  STATIC_PAGE_RESPONSE=$(execute_mutation "$STATIC_PAGE_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create static page. Exiting."
    exit 1
  fi
  STATIC_PAGE_ID=$(extract_field "$STATIC_PAGE_RESPONSE" '.data.testMode.createStaticPage.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract static page ID. Exiting."
    exit 1
  fi
  echo "Created static page with ID: $STATIC_PAGE_ID"

  # 8. Create another static page directly under root
  echo "Creating root static page..."
  ROOT_STATIC_PAGE_MUTATION="mutation { testMode { createStaticPage(planIdentifier: \"$PLAN_ID\", title: \"Root Static Page\") { id } } }"
  ROOT_STATIC_PAGE_RESPONSE=$(execute_mutation "$ROOT_STATIC_PAGE_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create root static page. Exiting."
    exit 1
  fi
  ROOT_STATIC_PAGE_ID=$(extract_field "$ROOT_STATIC_PAGE_RESPONSE" '.data.testMode.createStaticPage.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract root static page ID. Exiting."
    exit 1
  fi
  echo "Created root static page with ID: $ROOT_STATIC_PAGE_ID"

  # 9. Create actions
  echo "Creating actions..."
  for i in {1..5}; do
    ACTION_MUTATION="mutation { testMode { createAction(planIdentifier: \"$PLAN_ID\", name: \"Test Action $i\", identifier: \"action-$i\") { id uuid } } }"
    ACTION_RESPONSE=$(execute_mutation "$ACTION_MUTATION")
    if [ $? -ne 0 ]; then
      echo "Failed to create action $i. Exiting."
      exit 1
    fi
    ACTION_ID=$(extract_field "$ACTION_RESPONSE" '.data.testMode.createAction.id')
    if [ $? -ne 0 ]; then
      echo "Failed to extract action $i ID. Exiting."
      exit 1
    fi
    echo "Created action $i with ID: $ACTION_ID"

    # Store first action ID for later linking
    if [ $i -eq 1 ]; then
      FIRST_ACTION_ID=$ACTION_ID
    fi
  done

  # 10. Create category type
  echo "Creating category type..."
  CATEGORY_TYPE_MUTATION="mutation { testMode { createCategoryType(planIdentifier: \"$PLAN_ID\", name: \"Test Category Type\", identifier: \"test-category-type\") { id } } }"
  CATEGORY_TYPE_RESPONSE=$(execute_mutation "$CATEGORY_TYPE_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create category type. Exiting."
    exit 1
  fi
  CATEGORY_TYPE_ID=$(extract_field "$CATEGORY_TYPE_RESPONSE" '.data.testMode.createCategoryType.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract category type ID. Exiting."
    exit 1
  fi
  echo "Created category type with ID: $CATEGORY_TYPE_ID"

  # 11. Create category type page
  echo "Creating category type page..."
  CATEGORY_TYPE_PAGE_MUTATION="mutation { testMode { createCategoryTypePage(planIdentifier: \"$PLAN_ID\", title: \"Category Type Page\", categoryTypeId: $CATEGORY_TYPE_ID) { id } } }"
  CATEGORY_TYPE_PAGE_RESPONSE=$(execute_mutation "$CATEGORY_TYPE_PAGE_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create category type page. Exiting."
    exit 1
  fi
  CATEGORY_TYPE_PAGE_ID=$(extract_field "$CATEGORY_TYPE_PAGE_RESPONSE" '.data.testMode.createCategoryTypePage.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract category type page ID. Exiting."
    exit 1
  fi
  echo "Created category type page with ID: $CATEGORY_TYPE_PAGE_ID"

  # 12. Create category
  echo "Creating category..."
  CATEGORY_MUTATION="mutation { testMode { createCategory(planIdentifier: \"$PLAN_ID\", categoryTypeIdentifier: \"test-category-type\", name: \"Test Category\", identifier: \"test-category\") { id } } }"
  CATEGORY_RESPONSE=$(execute_mutation "$CATEGORY_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create category. Exiting."
    exit 1
  fi
  CATEGORY_ID=$(extract_field "$CATEGORY_RESPONSE" '.data.testMode.createCategory.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract category ID. Exiting."
    exit 1
  fi
  echo "Created category with ID: $CATEGORY_ID"

  # 13. Create category page
  echo "Creating category page..."
  CATEGORY_PAGE_MUTATION="mutation { testMode { createCategoryPage(planIdentifier: \"$PLAN_ID\", title: \"Test Category Page\", categoryId: $CATEGORY_ID) { id } } }"
  CATEGORY_PAGE_RESPONSE=$(execute_mutation "$CATEGORY_PAGE_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create category page. Exiting."
    exit 1
  fi
  CATEGORY_PAGE_ID=$(extract_field "$CATEGORY_PAGE_RESPONSE" '.data.testMode.createCategoryPage.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract category page ID. Exiting."
    exit 1
  fi
  echo "Created category page with ID: $CATEGORY_PAGE_ID"

  # 14. Create indicator
  echo "Creating indicator..."
  INDICATOR_MUTATION="mutation { testMode { createIndicator(planIdentifier: \"$PLAN_ID\", name: \"Test Indicator\") { id } } }"
  INDICATOR_RESPONSE=$(execute_mutation "$INDICATOR_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to create indicator. Exiting."
    exit 1
  fi
  INDICATOR_ID=$(extract_field "$INDICATOR_RESPONSE" '.data.testMode.createIndicator.id')
  if [ $? -ne 0 ]; then
    echo "Failed to extract indicator ID. Exiting."
    exit 1
  fi
  echo "Created indicator with ID: $INDICATOR_ID"

  # 15. Link action to category
  echo "Linking action to category..."
  LINK_AC_MUTATION="mutation { testMode { linkActionToCategory(actionId: $FIRST_ACTION_ID, categoryId: $CATEGORY_ID) } }"
  LINK_AC_RESPONSE=$(execute_mutation "$LINK_AC_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to link action to category. Exiting."
    exit 1
  fi
  LINK_AC_RESULT=$(extract_field "$LINK_AC_RESPONSE" '.data.testMode.linkActionToCategory')
  if [ $? -ne 0 ]; then
    echo "Failed to extract link action to category result. Exiting."
    exit 1
  fi
  echo "Linked action to category: $LINK_AC_RESULT"

  # 16. Link action to indicator
  echo "Linking action to indicator..."
  LINK_AI_MUTATION="mutation { testMode { linkActionToIndicator(actionId: $FIRST_ACTION_ID, indicatorId: $INDICATOR_ID) } }"
  LINK_AI_RESPONSE=$(execute_mutation "$LINK_AI_MUTATION")
  if [ $? -ne 0 ]; then
    echo "Failed to link action to indicator. Exiting."
    exit 1
  fi
  LINK_AI_RESULT=$(extract_field "$LINK_AI_RESPONSE" '.data.testMode.linkActionToIndicator')
  if [ $? -ne 0 ]; then
    echo "Failed to extract link action to indicator result. Exiting."
    exit 1
  fi
  echo "Linked action to indicator: $LINK_AI_RESULT"

  echo "=== Completed Plan ID: $PLAN_ID ==="
done

echo "=== Test data population complete ==="
echo "You can now run your e2e tests against the plans: $PLAN_IDS"
