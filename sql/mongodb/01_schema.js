// ═══════════════════════════════════════════════════════
//  MCS 504 DATABASE PROJECT — MONGODB SCHEMA & INDEXES
//  Idempotent script to set up validations and indexes
// ═══════════════════════════════════════════════════════

db = db.getSiblingDB("melissa-db");

// ═══════════════════════════════════════════════════════
//  1. COLLECTION SCHEMA VALIDATIONS
// ═══════════════════════════════════════════════════════

// Drop existing collections to ensure idempotency
db.stands.drop();
db.stand_survey.drop();
db.stand_subdivisions.drop();
db.stand_owners.drop();
db.dependents.drop();
db.stand_allocations.drop();
db.metadata_catalogue.drop();

// Entity 1: stands
db.createCollection("stands", {
   validator: {
      $jsonSchema: {
         bsonType: "object",
         required: [ "stand_number", "location", "size_m2", "activity", "gps_coordinates", "location_city" ],
         properties: {
            stand_number: {
               bsonType: "string",
               description: "Must be a unique VARCHAR-like string identifying the stand"
            },
            location: {
               bsonType: "string",
               description: "Full descriptive text location of the stand"
            },
            size_m2: {
               bsonType: "decimal",
               minimum: 0.01,
               description: "Stand size in square metres; must be a positive decimal number"
            },
            activity: {
               enum: [ "Residential", "Commercial" ],
               description: "Must be either Residential or Commercial"
            },
            picture_url: {
               bsonType: [ "string", "null" ],
               description: "Optional URL/path to physical stand image representation"
            },
            gps_coordinates: {
               bsonType: "object",
               required: [ "type", "coordinates" ],
               properties: {
                  type: {
                     enum: [ "Polygon" ]
                  },
                  coordinates: {
                     bsonType: "array",
                     description: "Must be a standard GeoJSON Polygon array of coordinate rings"
                  }
               }
            },
            location_city: {
               bsonType: "string",
               description: "City or town location name"
            }
         }
      }
   }
});

// Entity 2: stand_survey
db.createCollection("stand_survey", {
   validator: {
      $jsonSchema: {
         bsonType: "object",
         required: [ "stand_number", "survey_status", "province", "district" ],
         properties: {
            stand_number: { bsonType: "string" },
            survey_status: { bsonType: "bool" },
            province: { bsonType: "string" },
            district: { bsonType: "string" }
         }
      }
   }
});

// Entity 3: stand_subdivisions
db.createCollection("stand_subdivisions", {
   validator: {
      $jsonSchema: {
         bsonType: "object",
         required: [ "subdivision_id", "stand_number", "allocation_status", "size_m2" ],
         properties: {
            subdivision_id: { bsonType: "int" },
            stand_number: { bsonType: "string" },
            allocation_status: { bsonType: "bool" },
            size_m2: { bsonType: "decimal", minimum: 0.01 },
            remarks: { bsonType: [ "string", "null" ] }
         }
      }
   }
});

// Entity 4: stand_owners
db.createCollection("stand_owners", {
   validator: {
      $jsonSchema: {
         bsonType: "object",
         required: [ "stand_owner_id", "firstname", "date_of_birth", "gender", "disability_status", "province", "district" ],
         properties: {
            stand_owner_id: { bsonType: "int" },
            firstname: { bsonType: "string" },
            date_of_birth: { bsonType: "date" },
            gender: { enum: [ "Male", "Female", "Other" ] },
            disability_status: { bsonType: "bool" },
            province: { bsonType: "string" },
            district: { bsonType: "string" }
         }
      }
   }
});

// Entity 5: dependents
db.createCollection("dependents", {
   validator: {
      $jsonSchema: {
         bsonType: "object",
         required: [ "stand_owner_id", "firstname", "date_of_birth", "gender", "disability_status" ],
         properties: {
            stand_owner_id: { bsonType: "int" },
            firstname: { bsonType: "string" },
            date_of_birth: { bsonType: "date" },
            gender: { enum: [ "Male", "Female", "Other" ] },
            disability_status: { bsonType: "bool" }
         }
      }
   }
});

// Entity 6: stand_allocations
db.createCollection("stand_allocations", {
   validator: {
      $jsonSchema: {
         bsonType: "object",
         required: [ "allocation_id", "stand_owner_id", "subdivision_id", "date_of_allocation", "price_per_m2" ],
         properties: {
            allocation_id: { bsonType: "int" },
            stand_owner_id: { bsonType: "int" },
            subdivision_id: { bsonType: "int" },
            date_of_allocation: { bsonType: "date" },
            price_per_m2: { bsonType: "decimal", minimum: 0.01 }
         }
      }
   }
});


// ═══════════════════════════════════════════════════════
//  2. INDEX CREATIONS (Q7 REQUIREMENT)
// ═══════════════════════════════════════════════════════

// 1. PostGIS-equivalent Spatial 2dsphere index on stands boundary
db.stands.createIndex({ "gps_coordinates": "2dsphere" });

// 2. Text Search index on descriptive location
db.stands.createIndex({ "location": "text" });

// 3. Composite Index on Geography Location search
db.stand_survey.createIndex({ "province": 1, "district": 1 });
db.stand_owners.createIndex({ "province": 1, "district": 1 });

// 4. Partial Index on unallocated subdivisions (speeds up querying available slots)
db.stand_subdivisions.createIndex(
    { "subdivision_id": 1, "size_m2": 1 },
    { partialFilterExpression: { "allocation_status": false } }
);

// 5. Unique Indexes for Primary Key replacements
db.stands.createIndex({ "stand_number": 1 }, { unique: true });
db.stand_subdivisions.createIndex({ "subdivision_id": 1 }, { unique: true });
db.stand_owners.createIndex({ "stand_owner_id": 1 }, { unique: true });
db.stand_allocations.createIndex({ "allocation_id": 1 }, { unique: true });


// ═══════════════════════════════════════════════════════
//  3. SEED SEEDS GENERATOR (ZIMBABWE PLACE NAMES)
// ═══════════════════════════════════════════════════════

db.stands.insertMany([
  {
    stand_number: "STD-HAR-001",
    location: "Borrowdale Brooke Golf Estate, Section A",
    size_m2: NumberDecimal("4000.00"),
    activity: "Residential",
    picture_url: "http://images.lands.gov.zw/stands/std-har-001.png",
    gps_coordinates: {
      type: "Polygon",
      coordinates: [[[31.111, -17.722], [31.115, -17.722], [31.115, -17.726], [31.111, -17.726], [31.111, -17.722]]]
    },
    location_city: "Harare"
  },
  {
    stand_number: "STD-BUL-002",
    location: "Suburbs Road Near Ascot Mall",
    size_m2: NumberDecimal("3000.00"),
    activity: "Residential",
    picture_url: "http://images.lands.gov.zw/stands/std-bul-002.png",
    gps_coordinates: {
      type: "Polygon",
      coordinates: [[[28.601, -20.155], [28.605, -20.155], [28.605, -20.159], [28.601, -20.159], [28.601, -20.155]]]
    },
    location_city: "Bulawayo"
  },
  {
    stand_number: "STD-MUT-003",
    location: "Chitepo Main Street Boulevard Commercial Hub",
    size_m2: NumberDecimal("7500.00"),
    activity: "Commercial",
    picture_url: "http://images.lands.gov.zw/stands/std-mut-003.png",
    gps_coordinates: {
      type: "Polygon",
      coordinates: [[[32.668, -18.971], [32.674, -18.971], [32.674, -18.976], [32.668, -18.976], [32.668, -18.971]]]
    },
    location_city: "Mutare"
  },
  {
    stand_number: "STD-GWE-004",
    location: "Senga Industrial Area Main Bypass",
    size_m2: NumberDecimal("12000.00"),
    activity: "Commercial",
    picture_url: "http://images.lands.gov.zw/stands/std-gwe-004.png",
    gps_coordinates: {
      type: "Polygon",
      coordinates: [[[29.831, -19.461], [29.841, -19.461], [29.841, -19.469], [29.831, -19.469], [29.831, -19.461]]]
    },
    location_city: "Gweru"
  },
  {
    stand_number: "STD-MAS-005",
    location: "Rhodene High-density Layout Block D",
    size_m2: NumberDecimal("2500.00"),
    activity: "Residential",
    picture_url: "http://images.lands.gov.zw/stands/std-mas-005.png",
    gps_coordinates: {
      type: "Polygon",
      coordinates: [[[30.825, -20.065], [30.829, -20.065], [30.829, -20.069], [30.825, -20.069], [30.825, -20.065]]]
    },
    location_city: "Masvingo"
  }
]);

db.stand_survey.insertMany([
  { stand_number: "STD-HAR-001", survey_status: true, province: "Harare", district: "Harare Central" },
  { stand_number: "STD-BUL-002", survey_status: true, province: "Bulawayo", district: "Bulawayo Central" },
  { stand_number: "STD-MUT-003", survey_status: true, province: "Manicaland", district: "Mutare" },
  { stand_number: "STD-GWE-004", survey_status: true, province: "Midlands", district: "Gweru" },
  { stand_number: "STD-MAS-005", survey_status: true, province: "Masvingo", district: "Masvingo" }
]);

db.stand_subdivisions.insertMany([
  { subdivision_id: 1, stand_number: "STD-HAR-001", allocation_status: true, size_m2: NumberDecimal("1500.00"), remarks: "Divided Brooke plot East Wing" },
  { subdivision_id: 2, stand_number: "STD-HAR-001", allocation_status: false, size_m2: NumberDecimal("2000.00"), remarks: "Divided Brooke plot West Wing" },
  { subdivision_id: 3, stand_number: "STD-BUL-002", allocation_status: true, size_m2: NumberDecimal("1200.00"), remarks: "Ascot subdiv Sector 1" },
  { subdivision_id: 4, stand_number: "STD-BUL-002", allocation_status: false, size_m2: NumberDecimal("1500.00"), remarks: "Ascot subdiv Sector 2" },
  { subdivision_id: 5, stand_number: "STD-MUT-003", allocation_status: true, size_m2: NumberDecimal("3500.00"), remarks: "Commercial plaza division North" },
  { subdivision_id: 6, stand_number: "STD-MUT-003", allocation_status: false, size_m2: NumberDecimal("3000.00"), remarks: "Commercial plaza division South" },
  { subdivision_id: 7, stand_number: "STD-GWE-004", allocation_status: true, size_m2: NumberDecimal("6000.00"), remarks: "Senga Heavy Yard Subdivision A" },
  { subdivision_id: 8, stand_number: "STD-MAS-005", allocation_status: true, size_m2: NumberDecimal("1000.00"), remarks: "Rhodene Corner Lot A" },
  { subdivision_id: 9, stand_number: "STD-MAS-005", allocation_status: false, size_m2: NumberDecimal("1200.00"), remarks: "Rhodene Corner Lot B" }
]);

db.stand_owners.insertMany([
  { stand_owner_id: 1, firstname: "Tendai Mupfumi", date_of_birth: ISODate("1980-04-12T00:00:00Z"), gender: "Male", disability_status: false, province: "Harare", district: "Harare Central" },
  { stand_owner_id: 2, firstname: "Chipo Sibanda", date_of_birth: ISODate("1988-11-23T00:00:00Z"), gender: "Female", disability_status: true, province: "Bulawayo", district: "Bulawayo Central" },
  { stand_owner_id: 3, firstname: "Farai Mutasa", date_of_birth: ISODate("1975-06-30T00:00:00Z"), gender: "Male", disability_status: false, province: "Manicaland", district: "Mutare" },
  { stand_owner_id: 4, firstname: "Nyarai Zhou", date_of_birth: ISODate("1992-01-15T00:00:00Z"), gender: "Female", disability_status: false, province: "Midlands", district: "Gweru" },
  { stand_owner_id: 5, firstname: "Tinashe Moyo", date_of_birth: ISODate("1982-08-05T00:00:00Z"), gender: "Male", disability_status: true, province: "Masvingo", district: "Masvingo" }
]);

db.dependents.insertMany([
  { stand_owner_id: 1, firstname: "Rufaro Mupfumi", date_of_birth: ISODate("2010-05-14T00:00:00Z"), gender: "Female", disability_status: false },
  { stand_owner_id: 1, firstname: "Kundai Mupfumi", date_of_birth: ISODate("2015-09-20T00:00:00Z"), gender: "Male", disability_status: false },
  { stand_owner_id: 2, firstname: "Lindiwe Sibanda", date_of_birth: ISODate("2012-03-04T00:00:00Z"), gender: "Female", disability_status: true },
  { stand_owner_id: 3, firstname: "Tariro Mutasa", date_of_birth: ISODate("2008-07-22T00:00:00Z"), gender: "Female", disability_status: false },
  { stand_owner_id: 5, firstname: "Tatenda Moyo", date_of_birth: ISODate("2014-12-01T00:00:00Z"), gender: "Male", disability_status: false }
]);

db.stand_allocations.insertMany([
  { allocation_id: 1, stand_owner_id: 1, subdivision_id: 1, date_of_allocation: ISODate("2026-01-10T00:00:00Z"), price_per_m2: NumberDecimal("150.00") },
  { allocation_id: 2, stand_owner_id: 2, subdivision_id: 3, date_of_allocation: ISODate("2026-02-15T00:00:00Z"), price_per_m2: NumberDecimal("120.00") },
  { allocation_id: 3, stand_owner_id: 3, subdivision_id: 5, date_of_allocation: ISODate("2026-03-20T00:00:00Z"), price_per_m2: NumberDecimal("200.00") },
  { allocation_id: 4, stand_owner_id: 4, subdivision_id: 7, date_of_allocation: ISODate("2026-04-18T00:00:00Z"), price_per_m2: NumberDecimal("85.00") },
  { allocation_id: 5, stand_owner_id: 5, subdivision_id: 8, date_of_allocation: ISODate("2026-05-12T00:00:00Z"), price_per_m2: NumberDecimal("110.00") }
]);

db.metadata_catalogue.insertMany([
  { table_name: "stands", column_name: "stand_number", data_type: "string", is_pii: false, data_classification: "Public" },
  { table_name: "stands", column_name: "gps_coordinates", data_type: "geojson", is_pii: false, data_classification: "Internal" },
  { table_name: "stand_owners", column_name: "firstname", data_type: "string", is_pii: true, data_classification: "Confidential" },
  { table_name: "stand_owners", column_name: "date_of_birth", data_type: "date", is_pii: true, data_classification: "Confidential" },
  { table_name: "stand_owners", column_name: "gender", data_type: "string", is_pii: true, data_classification: "Confidential" },
  { table_name: "stand_owners", column_name: "disability_status", data_type: "boolean", is_pii: true, data_classification: "Confidential" },
  { table_name: "dependents", column_name: "firstname", data_type: "string", is_pii: true, data_classification: "Confidential" },
  { table_name: "dependents", column_name: "date_of_birth", data_type: "date", is_pii: true, data_classification: "Confidential" }
]);

print("MongoDB Land Stand schema validation, index creation, and Zimbabwean seed data fully applied!");
