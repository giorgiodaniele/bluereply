from   datetime import datetime, timezone
import pandas


def get_time_horizon():
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = now
    return int(start.timestamp()), int(end.timestamp())


# 
# FOCUS FORMAT 1.0
# 
FOCUS_SCHEMA_1_0 = [
    "AvailabilityZone",            # Recommended | Dimension | String | nullable
    "BilledCost",                  # Mandatory   | Metric    | Decimal | NOT NULL
    "BillingAccountId",            # Mandatory   | Dimension | String | NOT NULL
    "BillingAccountName",          # Mandatory   | Dimension | String | nullable
    "BillingCurrency",             # Mandatory   | Dimension | String | NOT NULL (ISO 4217)
    "BillingPeriodEnd",            # Mandatory   | Dimension | Date/Time | NOT NULL
    "BillingPeriodStart",          # Mandatory   | Dimension | Date/Time | NOT NULL
    "ChargeCategory",              # Mandatory   | Dimension | String | NOT NULL (allowed values)
    "ChargeClass",                 # Mandatory   | Dimension | String | nullable ("Correction"|null)
    "ChargeDescription",           # Mandatory   | Dimension | String | should not be null
    "ChargeFrequency",             # Recommended | Dimension | String | NOT NULL (allowed values)
    "ChargePeriodEnd",             # Mandatory   | Dimension | Date/Time | NOT NULL
    "ChargePeriodStart",           # Mandatory   | Dimension | Date/Time | NOT NULL
    "CommitmentDiscountCategory",  # Conditional | Dimension | String | nullable
    "CommitmentDiscountId",        # Conditional | Dimension | String | nullable
    "CommitmentDiscountName",      # Conditional | Dimension | String | nullable
    "CommitmentDiscountStatus",    # Conditional | Dimension | String | nullable
    "CommitmentDiscountType",      # Conditional | Dimension | String | nullable
    "ConsumedQuantity",            # Conditional | Metric    | Decimal | nullable
    "ConsumedUnit",                # Conditional | Metric    | String  | nullable
    "ContractedCost",              # Mandatory   | Metric    | Decimal | NOT NULL
    "ContractedUnitPrice",         # Conditional | Metric    | Decimal | nullable
    "EffectiveCost",               # Mandatory   | Metric    | Decimal | NOT NULL
    "InvoiceIssuerName",           # Mandatory   | Dimension | String | NOT NULL
    "ListCost",                    # Mandatory   | Metric    | Decimal | NOT NULL
    "ListUnitPrice",               # Conditional | Metric    | Decimal | nullable
    "PricingCategory",             # Conditional | Dimension | String | nullable
    "PricingQuantity",             # Mandatory   | Metric    | Decimal | nullable
    "PricingUnit",                 # Mandatory   | Dimension | String | nullable
    "ProviderName",                # Mandatory   | Dimension | String | NOT NULL
    "PublisherName",               # Mandatory   | Dimension | String | NOT NULL
    "RegionId",                    # Conditional | Dimension | String | nullable
    "RegionName",                  # Conditional | Dimension | String | nullable
    "ResourceId",                  # Conditional | Dimension | String | nullable
    "ResourceName",                # Conditional | Dimension | String | nullable
    "ResourceType",                # Conditional | Dimension | String | nullable
    "ServiceCategory",             # Mandatory   | Dimension | String | NOT NULL (allowed values)
    "ServiceName",                 # Mandatory   | Dimension | String | NOT NULL
    "SkuId",                       # Conditional | Dimension | String | nullable
    "SkuPriceId",                  # Conditional | Dimension | String | nullable
    "SubAccountId",                # Conditional | Dimension | String | nullable
    "SubAccountName",              # Conditional | Dimension | String | nullable
    "Tags",                        # Conditional | Dimension | JSON   | nullable
]


SERVICE_CATEGORY_AI          = "AI and Machine Learning"
CHARGE_CATEGORY_USAGE        = "Usage"
CHARGE_FREQUENCY_USAGE_BASED = "Usage-Based"
PRICING_CATEGORY_STANDARD    = "Standard"

def parse_line_item(value: str):
    if pandas.isna(value):
        return None, None

    parts = [p.strip() for p in value.split(",")]
    if len(parts) == 1:
        return parts[0], "usage"

    return parts[0], parts[1]


def classify_model(model_name: str):
    if model_name is None:
        return SERVICE_CATEGORY_AI, "Unknown"

    name = model_name.lower()

    if "embedding" in name:
        return SERVICE_CATEGORY_AI, "OpenAI Embeddings"
    if "gpt" in name:
        return SERVICE_CATEGORY_AI, "OpenAI GPT"
    if "transcribe" in name or "speech" in name or "whisper" in name or "tts" in name:
        return SERVICE_CATEGORY_AI, "OpenAI Audio"
    if "image" in name or "dall" in name:
        return SERVICE_CATEGORY_AI, "OpenAI Image"

    return SERVICE_CATEGORY_AI, "OpenAI Other"


def build_charge_description(model: str, usage_type: str) -> str:
    if model is None and usage_type is None:
        return "OpenAI API usage"

    model_part = model or "unknown model"
    if usage_type is None:
        return f"OpenAI {model_part} usage"

    ut = usage_type.lower()
    if "input" in ut and "cached" in ut:
        return f"OpenAI {model_part} - cached input tokens"
    if "input" in ut:
        return f"OpenAI {model_part} - input tokens"
    if "output" in ut:
        return f"OpenAI {model_part} - output tokens"
    if "cached" in ut:
        return f"OpenAI {model_part} - cached tokens"

    return f"OpenAI {model_part} - {usage_type}"


def to_iso8601_utc(epoch_seconds) -> str:
    if pandas.isna(epoch_seconds):
        return None
    return datetime.fromtimestamp(int(epoch_seconds), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def generate_focus(
    frame: pandas.DataFrame,
    start_time,
    end_time,
    organization_id,
    organization_name,
    project_id,
    project_name,
) -> pandas.DataFrame:
    
    df = frame.copy()

    # 
    # Parsing line_item OpenAI
    # 
    parsed = df["line_item"].apply(parse_line_item)
    df["_ModelName"] = parsed.apply(lambda x: x[0])
    df["_UsageType"] = parsed.apply(lambda x: x[1])

    # 
    # Define class service
    # 
    classified = df["_ModelName"].apply(classify_model)
    df["ServiceCategory"] = classified.apply(lambda x: x[0])
    df["ServiceName"] = classified.apply(lambda x: x[1])

    # 
    # ChargeDescription: input/output/cached
    # 
    df["ChargeDescription"] = df.apply(
        lambda r: build_charge_description(r["_ModelName"], r["_UsageType"]),
        axis=1,
    )


    df["ChargeCategory"]  = CHARGE_CATEGORY_USAGE
    df["ChargeClass"]     = None
    df["ChargeFrequency"] = CHARGE_FREQUENCY_USAGE_BASED

    #
    # Anything about costs
    #
    df["BilledCost"]      = df["amount_value"].fillna(0).astype(float)
    df["EffectiveCost"]   = df["BilledCost"]
    df["ContractedCost"]  = df["BilledCost"]
    df["ListCost"]        = df["BilledCost"]
    df["BillingCurrency"] = df["amount_currency"].str.upper()

    # 
    # Pricing
    # 
    df["PricingCategory"]     = PRICING_CATEGORY_STANDARD
    df["PricingQuantity"]     = None
    df["PricingUnit"]         = None
    df["ListUnitPrice"]       = None
    df["ContractedUnitPrice"] = None

    # 
    # Format dates
    # 
    df["BillingPeriodStart"] = to_iso8601_utc(start_time)
    df["BillingPeriodEnd"]   = to_iso8601_utc(end_time)
    df["ChargePeriodStart"]  = df["start_time"].apply(to_iso8601_utc)
    df["ChargePeriodEnd"]    = df["end_time"].apply(to_iso8601_utc)

    #
    # Account / Subaccount
    #
    df["BillingAccountId"]   = organization_id
    df["BillingAccountName"] = organization_name
    df["SubAccountId"]       = project_id
    df["SubAccountName"]     = project_name

    # 
    # CLoud provider is always OpenAI
    # 
    df["ProviderName"]     = "OpenAI"
    df["PublisherName"]     = "OpenAI"
    df["InvoiceIssuerName"] = "OpenAI"

    # 
    # Resource
    # 
    df["ResourceId"]   = df["_ModelName"]
    df["ResourceName"] = df["_ModelName"]
    df["ResourceType"] = "AI Model"

    # 
    # Consumed Quantity / Unit (token o richieste, se disponibili)
    # 
    if "num_tokens" in df.columns:
        df["ConsumedQuantity"] = df["num_tokens"]
        df["ConsumedUnit"] = "Tokens"
    elif "num_requests" in df.columns:
        df["ConsumedQuantity"] = df["num_requests"]
        df["ConsumedUnit"] = "Requests"
    else:
        df["ConsumedQuantity"] = None
        df["ConsumedUnit"] = None

    # 
    # Region / Availability Zone: OpenAI does not have a one
    # 
    df["RegionId"]         = None
    df["RegionName"]       = None
    df["AvailabilityZone"] = None

    # 
    # SKU: OpenAI does not hava a one
    # 
    df["SkuId"]      = None
    df["SkuPriceId"] = None

    # 
    # Commitment Discount: OpenAI is only PAYG
    # 
    df["CommitmentDiscountId"]        = None
    df["CommitmentDiscountName"]      = None
    df["CommitmentDiscountCategory"]  = None
    df["CommitmentDiscountStatus"]    = None
    df["CommitmentDiscountType"]      = None

    # 
    # Force all columns
    # 
    for col in FOCUS_SCHEMA_1_0:
        if col not in df.columns:
            df[col] = None

    return df[FOCUS_SCHEMA_1_0]