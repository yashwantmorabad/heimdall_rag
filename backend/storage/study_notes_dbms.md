# DBMS Study Notes

## Normalization

Normalization is the process of organizing data in a database to reduce redundancy and improve data integrity.

### First Normal Form (1NF)
- Each column contains atomic values
- No repeating groups
- Each row is unique

### Second Normal Form (2NF)
- Must be in 1NF
- No partial dependencies (non-key attributes depend on whole primary key)

### Third Normal Form (3NF)
- Must be in 2NF
- No transitive dependencies (non-key attributes depend only on primary key)

## ACID Properties

**Atomicity**: Transactions are all-or-nothing
**Consistency**: Database moves from one valid state to another
**Isolation**: Concurrent transactions don't interfere
**Durability**: Committed transactions survive failures

## Indexes

- B-tree indexes: good for range queries
- Hash indexes: good for equality lookups
- Composite indexes: multiple columns, order matters
