import requests
import json

RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"

def get_rxcui(drug_name):
    """
    Fetch the RxCUI (RxNorm Concept Unique Identifier) for a given drug name.
    """
    url = f"{RXNORM_BASE}/rxcui.json"
    params = {"name": drug_name}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("idGroup", {}).get("rxnormId", [None])[0]

def check_interactions(rxcui_list):
    """
    Given a list of RxCUIs, check for known drug interactions using the RxNorm Interaction API.
    """
    joined_ids = "+".join(rxcui_list)
    url = f"{RXNORM_BASE}/interaction/list.json?rxcuis={joined_ids}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    interactions = []
    groups = data.get("fullInteractionTypeGroup", [])
    for group in groups:
        for interaction_type in group.get("fullInteractionType", []):
            for interaction_pair in interaction_type.get("interactionPair", []):
                interaction = {
                    "description": interaction_pair.get("description"),
                    "severity": interaction_pair.get("severity"),
                    "drugs": [concept["name"] for concept in interaction_pair["interactionConcept"]]
                }
                interactions.append(interaction)
    return interactions

def main(drug_names):
    """
    Main function to get drug interactions.
    """
    print("Getting RxCUIs for:", drug_names)
    rxcui_list = []
    for name in drug_names:
        rxcui = get_rxcui(name)
        if rxcui:
            print(f"  {name} → RxCUI: {rxcui}")
            rxcui_list.append(rxcui)
        else:
            print(f"  {name} → RxCUI not found.")

    if len(rxcui_list) < 2:
        print("\nNeed at least 2 valid drugs to check for conflicts.")
        return

    print("\nChecking for interactions...")
    interactions = check_interactions(rxcui_list)
    if not interactions:
        print("No conflicts found.")
    else:
        print(f"Found {len(interactions)} potential interaction(s):\n")
        for idx, interaction in enumerate(interactions, 1):
            print(f"{idx}. Drugs: {', '.join(interaction['drugs'])}")
            print(f"   Severity: {interaction['severity']}")
            print(f"   Description: {interaction['description']}\n")

if __name__ == '__main__':
    # Example: Replace with dynamic input or pass from CLI, UI, etc.
    user_input_drugs = input("Enter medicine names separated by comma: ")
    drug_list = [d.strip() for d in user_input_drugs.split(",") if d.strip()]
    main(drug_list)
