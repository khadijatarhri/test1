import sys  
import traceback  
  
try:  
    print("Tentative d'importation du module db_connections...")  
    from db_connections import client, db  
    print("Module db_connections importé avec succès!")  
      
    try:  
        print("Tentative de connexion à MongoDB...")  
        info = client.server_info()  
        print("Connexion à MongoDB réussie!")  
        print(f"Version du serveur MongoDB: {info.get('version', 'inconnue')}")  
          
        print("\nCollections dans la base de données PFADB:")  
        collections = db.list_collection_names()  
        if collections:  
            for collection in collections:  
                print(f"- {collection}")  
        else:  
            print("Aucune collection trouvée dans la base de données.")  
          
        if 'users' in collections:  
            print("\nLa collection 'users' existe.")  
            user_count = db.users.count_documents({})  
            print(f"Nombre d'utilisateurs dans la collection: {user_count}")  
              
            if user_count > 0:  
                first_user = db.users.find_one({})  
                if first_user:  
                    user_display = {k: v for k, v in first_user.items() if k != 'password'}  
                    print("\nPremier utilisateur trouvé:")  
                    print(user_display)  
        else:  
            print("\nLa collection 'users' n'existe pas encore.")  
              
    except Exception as e:  
        print(f"Erreur lors de la connexion à MongoDB: {e}")  
        print("\nTraceback complet:")  
        traceback.print_exc()  
          
except ImportError as e:  
    print(f"Erreur d'importation: {e}")  
    print("\nVérifiez que le fichier db_connections.py est dans le même répertoire ou dans le PYTHONPATH.")  
    print("Répertoire courant:", sys.path[0])  
    print("PYTHONPATH:", sys.path)  
except Exception as e:  
    print(f"Erreur inattendue: {e}")  
    print("\nTraceback complet:")  
    traceback.print_exc()  
  
print("\nFin du script de test.")