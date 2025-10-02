import requests
import json

def test_nsfw_parameters():
    """
    NSFW パラメータの正確な値をテスト
    """

    # Test different NSFW parameter formats
    nsfw_variations = {
        "None_string": "None",
        "Soft_string": "Soft",
        "Mature_string": "Mature",
        "X_string": "X",
        "none_lower": "none",
        "soft_lower": "soft",
        "mature_lower": "mature",
        "x_lower": "x",
        "boolean_false": "false",
        "boolean_true": "true",
        "no_nsfw": None  # パラメータなし
    }

    # Valid sort parameters (from previous testing)
    valid_sorts = ["Most Reactions", "Newest", "Oldest"]

    base_params = {
        'modelVersionId': '2091367',
        'limit': 10
    }

    print("🔍 NSFW Parameter Testing:")
    print("=" * 50)

    for nsfw_name, nsfw_value in nsfw_variations.items():
        for sort_strategy in valid_sorts[:2]:  # Test first 2 sorts only
            try:
                params = base_params.copy()
                params['sort'] = sort_strategy

                if nsfw_value is not None:
                    params['nsfw'] = nsfw_value

                print(f"\n📊 Testing: {nsfw_name} + {sort_strategy}")
                print(f"   Parameters: {params}")

                response = requests.get(
                    "https://civitai.com/api/v1/images",
                    params=params,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    items_count = len(data.get('items', []))
                    print(f"   ✅ SUCCESS: {items_count} items")
                else:
                    print(f"   ❌ FAILED: HTTP {response.status_code}")
                    if response.status_code == 400:
                        try:
                            error_data = response.json()
                            print(f"   Error details: {error_data}")
                        except:
                            print(f"   Error text: {response.text[:200]}")

            except Exception as e:
                print(f"   🔥 EXCEPTION: {e}")

if __name__ == "__main__":
    test_nsfw_parameters()
