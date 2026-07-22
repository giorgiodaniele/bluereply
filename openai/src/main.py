import os
import csv
import dotenv
import pandas

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib  import Path
from openai   import OpenAI


dotenv.load_dotenv()

OPENAI_ORGANIZATION_ID   = os.getenv("OPENAI_ORGANIZATION_ID")
OPENAI_ORGANIZATION_NAME = os.getenv("OPENAI_ORGANIZATION_NAME")
OPENAI_SECRET_KEY        = os.getenv("OPENAI_SECRET_KEY")
OUTPUT_DIRECTORY         = Path(f"out_{datetime.today():%Y%m%d_%H%M%S}")


def extract_costs():
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

    ts = int((datetime.today() - timedelta(days=30)).timestamp())
    te = int((datetime.today() - timedelta(days=1)).timestamp())

    # Generate a new client and requests costs from OpenAI
    client = OpenAI(admin_api_key=OPENAI_SECRET_KEY, organization=OPENAI_ORGANIZATION_ID, timeout=120, max_retries=10)
    page   = None
    data   = []
    while True:
        res = client.admin.organization.usage.costs(start_time=ts, end_time=te, bucket_width="1d", group_by=["line_item", "project_id"], limit=31, page=page)
        for bucket in res.data:
            for item in bucket.results:
                data.append({
                    "start_time": str(bucket.start_time)  if bucket.start_time is not None else None,
                    "end_time": str(bucket.end_time)      if bucket.end_time is not None else None,
                    "currency": str(item.amount.currency) if item.amount.currency is not None else None,
                    "value": str(item.amount.value)       if item.amount.value is not None else None,
                    "api_key_id": str(item.api_key_id)    if item.api_key_id is not None else None,
                    "line_item": str(item.line_item)             if item.line_item is not None else None,
                    "organization_id": str(item.organization_id) if item.organization_id is not None else None,
                    "project_id": str(item.project_id)           if item.project_id is not None else None,
                    "quantity": str(item.quantity)               if item.quantity is not None else None,
                })
        if not res.has_more:
            break
        page  = res.next_page

    # Generate a pandas dataframe
    frame = pandas.DataFrame(data)
    frame.to_csv(f"{OUTPUT_DIRECTORY}/costs.csv", index=False)
    return frame


def iso(ts):
    if not ts:
        return ""
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()


def to_focus():

    frame    = pandas.read_csv(OUTPUT_DIRECTORY / "costs.csv", dtype_backend="numpy_nullable")
    focus    = frame.copy()
    focus[:] = ""

    focus["AvailabilityZone"]   = ""
    focus["BilledCost"]         = frame["amount"]
    focus["BillingAccountId"]   = OPENAI_ORGANIZATION_ID
    focus["BillingAccountName"] = OPENAI_ORGANIZATION_NAME
    focus["BillingCurrency"]    = frame["currency"]
    focus["ChargeCategory"]     = "Usage"
    focus["ChargeClass"]        = "Usage"
    focus["ChargeDescription"]  = frame["line_item"]
    focus["ChargeFrequency"]    = "UsageBased"
    focus["ChargePeriodStart"]  = frame["start_time"].apply(iso)
    focus["ChargePeriodEnd"]    = frame["end_time"].apply(iso)
    focus["ConsumedQuantity"]   = frame["quantity"]
    focus["EffectiveCost"]      = frame["amount"]
    focus["ProviderName"]       = "OpenAI"
    focus["PublisherName"]      = "OpenAI"
    focus["RegionId"]           = "global"
    focus["RegionName"]         = "Global"
    focus["ResourceId"]         = frame["api_key_id"]
    focus["ResourceName"]       = frame["api_key_id"]
    focus["ServiceCategory"]    = "AI"
    focus["ServiceName"]        = "OpenAI API"
    focus["SkuName"]            = frame["line_item"]
    focus["SubAccountId"]       = frame["project_id"]
    focus["SubAccountName"]     = frame["project_id"]

    return focus



FOCUS_1_2_COLUMNS = [
    "AvailabilityZone",
    "BilledCost",
    "BillingAccountId",
    "BillingAccountName",
    "BillingAccountType",
    "BillingCurrency",
    "ChargeCategory",
    "ChargeClass",
    "ChargeDescription",
    "ChargeFrequency",
    "ChargePeriodEnd",
    "ChargePeriodStart",
    "CommitmentDiscountCategory",
    "CommitmentDiscountId",
    "CommitmentDiscountName",
    "CommitmentDiscountStatus",
    "CommitmentDiscountType",
    "ConsumedQuantity",
    "ConsumedUnit",
    "ContractedCost",
    "ContractedUnitPrice",
    "EffectiveCost",
    "InvoiceId",
    "ListCost",
    "ListUnitPrice",
    "PricingCategory",
    "PricingCurrency",
    "PricingCurrencyContractedCost",
    "PricingCurrencyContractedUnitPrice",
    "PricingCurrencyEffectiveCost",
    "PricingCurrencyListCost",
    "PricingCurrencyListUnitPrice",
    "ProviderName",
    "PublisherName",
    "RegionId",
    "RegionName",
    "ResourceId",
    "ResourceName",
    "ResourceType",
    "ServiceCategory",
    "ServiceName",
    "SkuId",
    "SkuPriceId",
    "SkuPriceDetails",
    "SkuMeter",
    "SkuName",
    "SubAccountId",
    "SubAccountName",
    "SubAccountType",
    "Tags"
]





#
# MAIN 
#
if __name__ == "__main__":

    # Save costs on disk
    frame = extract_costs()

    # focus = to_focus(costs)
    # focus.to_csv(OUTPUT_DIRECTORY / "focus.csv", index=False)
