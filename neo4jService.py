import json
import copy
from neo4j import GraphDatabase
import logging
from flask import request, jsonify

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Neo4jService:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        self.driver.close()

    def flatten_oid_fields(self, data):
        """Recursively replace Mongo-style ObjectId and Date fields with primitive values."""
        if isinstance(data, dict):
            if "$oid" in data and len(data) == 1:
                return data["$oid"]
            elif "$date" in data and len(data) == 1:
                return data["$date"]
            else:
                return {k: self.flatten_oid_fields(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.flatten_oid_fields(i) for i in data]
        else:
            return data

    
    def handle_neo4j_upload(self, file_field_name, creator_func):
        """
        Flask-compatible helper to process uploaded JSON files and insert them into Neo4j.
        Should be called from a Flask route.
        """
        try:
            logger.info(f"📤 Handling Neo4j upload for: {file_field_name}")

            if file_field_name not in request.files:
                logger.warning(f"❌ Missing file part: {file_field_name}")
                return jsonify({"error": f"No file part named '{file_field_name}' in the request"}), 400

            file = request.files[file_field_name]
            if file.filename == "":
                logger.warning(f"❌ Empty filename in upload: {file_field_name}")
                return jsonify({"error": "No file selected"}), 400

            data = json.load(file)
            logger.info(f"📦 Loaded {len(data)} records for {file_field_name}")

            cleaned_data = [self.flatten_oid_fields(item) for item in data]
            creator_func(self, cleaned_data)

            logger.info(f"✅ {file_field_name.capitalize()} data saved to Neo4j")
            return jsonify({"message": f"✅ {file_field_name.capitalize()} data updated"}), 200

        except Exception as e:
            logger.exception(f"❌ Error handling upload for {file_field_name}")
            return jsonify({"error": str(e)}), 500
    
    def load_clients_from_json(self, path):
        with open(path, "r") as f:
            raw_clients = json.load(f)
        return [self.flatten_oid_fields(c) for c in raw_clients]

    def load_items_from_json(self, path):
        with open(path, "r") as f:
            raw_items = json.load(f)
        return [self.flatten_oid_fields(i) for i in raw_items]
    
    def _run_create_client_query(self, tx, client):
        tx.run("""
            MERGE (c:Client {company: $company})
            SET c.commercial_name = $commercial_name,
                c.description = $description,
                c.emails = $emails,
                c.phones = $phones,
                c.creator_id = $creator_id,
                c.created_at = $created_at,
                c.updated_at = $updated_at,
                c.mongo_id = $mongo_id
        """,
        company=client["company"],
        commercial_name=client.get("commercial_name", ""),
        description=client.get("description", ""),
        emails=client.get("emails") or [],
        phones=client.get("phones") or [],
        creator_id=client.get("creator"),
        created_at=client.get("createdAt"),
        updated_at=client.get("updatedAt"),
        mongo_id=client.get("_id"))

    def create_clients(self, clients):
        with self.driver.session() as session:
            for client in clients:
                session.execute_write(self._run_create_client_query, client)
    
    def add_new_client(self, client):
        with self.driver.session() as session:
            session.execute_write(self._run_create_client_query, client)

    def create_items(self, items):
        def _create(tx, items):
            for item in items:
                warehouse_ids = [w.get("warehouseId") for w in item.get("warehouses", [])]
                tx.run("""
                    MERGE (i:Item {name: $name})
                    SET i.englishName = $englishName,
                        i.totalProductQuantity = $quantity,
                        i.unit = $unit,
                        i.threshold = $threshold,
                        i.category_id = $category_id,
                        i.creator_id = $creator_id,
                        i.warehouse_ids = $warehouse_ids,
                        i.mongo_id = $mongo_id
                """,
                name=item["name"],
                englishName=item.get("englishName", ""),
                quantity=item.get("totalProductQuantity", 0),
                unit=item.get("unit", ""),
                threshold=item.get("threshold", 0),
                category_id=item.get("category"),
                creator_id=item.get("creator"),
                warehouse_ids=warehouse_ids,
                mongo_id=item.get("_id")
                )
        with self.driver.session() as session:
            session.execute_write(_create, items)

    def delete_all_nodes_by_label(self, label):
        with self.driver.session() as session:
            session.run(f"""
                MATCH (n:{label})
                DETACH DELETE n
            """)


    def find_supplier(self, company_name, client_email, threshold=13):
        def _find(tx):
            result = tx.run("""
                MATCH (c:Client)
                WITH c,
                    apoc.text.distance(toLower(c.company), toLower($company_name)) AS dist_company_name

                WITH c,
                    apoc.coll.min([
                        dist_company_name
                    ]) AS final_score

                ORDER BY final_score ASC
                RETURN c, final_score
                LIMIT 1
            """, company_name=company_name, client_email=client_email)

            record = result.single()
            if record:
                print("📊 Final score:", record["final_score"])
            return dict(record["c"]) if record and record["final_score"] < threshold else None

        with self.driver.session() as session:
            return session.execute_read(_find)

    def find_item(self, description):
        def _find(tx):
            result = tx.run("""
                MATCH (i:Item)
                WITH i, apoc.text.distance(toLower(i.name), toLower($desc)) AS score
                ORDER BY score ASC
                RETURN i, score
                LIMIT 1
            """, desc=description)
            record = result.single()
            return dict(record["i"]) if record and record["score"] < 10 else None

        with self.driver.session() as session:
            return session.execute_read(_find)

    def enrich_invoice(self, invoice):
        """
        Adds supplier and item info to invoice by matching with existing graph data.
        """
        enriched_invoice = copy.deepcopy(invoice)


        enriched_invoice["supplier"] = self.find_supplier(
            invoice["provider"]["name"],
            invoice["provider"]["contact"]["email"]
        )

        enriched_items = []
        for item in invoice["items"]:
            enriched_item = item.copy()
            enriched_item["product"] = self.find_item(item["description"])
            enriched_items.append(enriched_item)

        enriched_invoice["items"] = enriched_items
        return enriched_invoice
