# QA Findings

Generated: 2025-10-22 22:49:34
Environment: Python 3.12.12 | Darwin 25.0.0

## Summary

- Total tests: 13
- Failures: 9
- Errors: 0
- Skipped: 9
- Time: 9.11s

## Artifacts


## Suites

### schemathesis (examples/petstore-api/tests/results/junit.xml)
- tests: 13 | failures: 9 | errors: 0 | skipped: 9 | time: 9.11s
- Notable cases:
  - FAILED: POST /pets (0.20s)
    - 1. Test Case ID: JQ7QpB  - Undocumented HTTP status code      Received: 422     Documented: 201, 400  [422] Unprocessable Entity:      `{"detail":[{"type":"missing","loc":["body","species"],"msg":"Field required","input":{"name":"Fluffy","age":null,"tags":["friendly","therapy"],"owner_id":null}}]}` 
  - FAILED: GET /pets/{pet_id} (0.06s)
    - 1. Test Case ID: NqEwK6  - Undocumented HTTP status code      Received: 422     Documented: 200, 404  [422] Unprocessable Entity:      `{"detail":[{"type":"int_parsing","loc":["path","pet_id"],"msg":"Input should be a valid integer, unable to parse string as an integer","input":"null,null"}]}`  Repr
  - FAILED: PUT /pets/{pet_id} (0.04s)
    - 1. Test Case ID: D71Eod  - Undocumented HTTP status code      Received: 422     Documented: 200, 400, 404  [422] Unprocessable Entity:      `{"detail":[{"type":"int_parsing","loc":["path","pet_id"],"msg":"Input should be a valid integer, unable to parse string as an integer","input":"null,null"}]}` 
  - FAILED: DELETE /pets/{pet_id} (0.06s)
    - 1. Test Case ID: 4iGjTT  - Undocumented HTTP status code      Received: 422     Documented: 204, 404  [422] Unprocessable Entity:      `{"detail":[{"type":"int_parsing","loc":["path","pet_id"],"msg":"Input should be a valid integer, unable to parse string as an integer","input":"null,null"}]}`  Repr
  - FAILED: GET /pets/search (0.01s)
    - 1. Test Case ID: Abm49l  - Undocumented HTTP status code      Received: 422     Documented: 200  [422] Unprocessable Entity:      `{"detail":[{"type":"int_parsing","loc":["path","pet_id"],"msg":"Input should be a valid integer, unable to parse string as an integer","input":"search"}]}`  Reproduce wi
  - FAILED: POST /owners (0.03s)
    - 1. Test Case ID: z5MLL2  - Undocumented HTTP status code      Received: 422     Documented: 201  [422] Unprocessable Entity:      `{"detail":[{"type":"missing","loc":["body","name"],"msg":"Field required","input":{"email":null}}]}`  Reproduce with:       curl -X POST -H 'Content-Type: application/js
  - FAILED: GET /owners/{owner_id} (0.06s)
    - 1. Test Case ID: o7LCXf  - Undocumented HTTP status code      Received: 422     Documented: 200, 404  [422] Unprocessable Entity:      `{"detail":[{"type":"int_parsing","loc":["path","owner_id"],"msg":"Input should be a valid integer, unable to parse string as an integer","input":"null,null"}]}`  Re
  - FAILED: GET /owners/{owner_id}/pets (0.06s)
    - 1. Test Case ID: EB5eKx  - Undocumented HTTP status code      Received: 422     Documented: 200, 404  [422] Unprocessable Entity:      `{"detail":[{"type":"int_parsing","loc":["path","owner_id"],"msg":"Input should be a valid integer, unable to parse string as an integer","input":"null,null"}]}`  Re
  - FAILED: Stateful tests (8.42s)
    - 1. Test Case ID: oB1ByE  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 5xx  [400] Bad Request:      `{"detail":"Owner -17828 does not exist."}`  Reproduce with:       curl -X POST -H 'Content-Type: application/json' -d '{"name": "
