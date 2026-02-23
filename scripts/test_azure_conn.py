import os
from azure.storage.filedatalake import DataLakeServiceClient
from dotenv import load_dotenv

def test_azure_connection():
    """
    Test connectivity to the Azure Data Lake Storage Gen2 using credentials from .env
    """
    load_dotenv()
    
    account_name = os.getenv("DATALAKE_NAME")
    account_key = os.getenv("DATALAKE_ACCESS_KEY")
    
    if not account_name or not account_key:
        print("❌ Error: DATALAKE_NAME or DATALAKE_ACCESS_KEY not found in .env")
        return

    try:
        service_client = DataLakeServiceClient(
            account_url=f"https://{account_name}.dfs.core.windows.net",
            credential=account_key
        )
        # Try to list file systems
        file_systems = service_client.list_file_systems()
        print(f"✅ Successfully connected to: {account_name}")
        print("📁 Available containers:")
        for fs in file_systems:
            print(f" - {fs.name}")
            
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")

if __name__ == "__main__":
    test_azure_connection()
