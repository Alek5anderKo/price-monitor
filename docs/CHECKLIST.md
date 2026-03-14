# CHECKLIST

## Stage 1 — correctness
- [ ] Verify DB initialization logic
- [ ] Verify table schema matches project needs
- [ ] Verify indexes are useful and valid
- [ ] Verify save_prices works correctly for all records
- [ ] Check connection handling
- [ ] Check commit/rollback behavior
- [ ] Check naming consistency
- [ ] Check error handling
- [ ] Check edge cases: empty prices, missing fields, invalid price
- [ ] Check duplicate insert behavior if relevant

## Stage 2 — optimization
- [ ] Remove repeated literals and magic values
- [ ] Centralize configuration
- [ ] Improve module boundaries
- [ ] Add logging
- [ ] Improve performance of inserts if needed
- [ ] Prepare for tests

## Stage 3 — next implementation
- [ ] Add comparison with previous prices
- [ ] Add change detection
- [ ] Add reporting / alert preparation
- [ ] Add scheduling strategy
- [ ] Add tests
- [ ] Prepare deployment approach
