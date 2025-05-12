import time


def transform_invoice(original_invoice):
  transformed = {
        "_id": '',
        "paymentType": None,
        "description": original_invoice.get("description", ""),
        "code": original_invoice.get("invoice_number",0),
        "multiAttachment": [],
        "paymentStatus": "unpaid",
        "status": "pending",
        "dueDate": original_invoice.get("invoice_date",None),
        "paymentStatusHistory": [],
        "group": None,
        "tag": None,
        "approvers": [],
        "paymentDate": original_invoice.get("invoice_date",None),
        "totalAmount": original_invoice.get("total",{}),
        "VAT_NUMBER":original_invoice.get("VAT_NUMBER/NIE/CIF",''),
        "invoiceProducts": [
            {
                "name": item["description"],
                "price": item["unit_price"],
                "total": item["total"],
                "tax": 0 if not original_invoice["total"]["VAT_rate"] else original_invoice["total"]["VAT_rate"],
                "quantity": item["quantity"],
                "product": None,
                "taxes": [],  
                "irpfValue": 0,
                "_id": str(int(time.time() * 1000)),
            } for item in original_invoice["items"]
        ],
    }
  supplier = original_invoice.get("supplier")
  if supplier and "mongo_id" in supplier:
      transformed["supplier"] = {
          "_id": supplier["mongo_id"],
          "company": supplier.get("company"),
          "commercial_name": supplier.get("commercial_name")
      }
  else:
      transformed["supplier"] = None
  return transformed

  
