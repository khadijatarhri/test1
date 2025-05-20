from django.shortcuts import render

# Create your views here.
import csv  
import io  
import json  
from django.shortcuts import render, redirect  
from django.http import HttpResponse, JsonResponse  
from django.views import View  
from django.contrib.auth.mixins import LoginRequiredMixin  
from pymongo import MongoClient  
from presidio_analyzer import AnalyzerEngine  
from presidio_anonymizer import AnonymizerEngine  
from presidio_anonymizer.entities import RecognizerResult, OperatorConfig  
from .models import AnonymizationJob  
from django.contrib.auth.models import User

# Connexion à MongoDB  
client = MongoClient('mongodb://localhost:27017/')  
db = client['csv_anonymizer_db']  
collection = db['csv_data']  
  
  
class UploadCSVView(View):
    def get(self, request):
        if not request.session.get("user_email"):
            return redirect('login_form')
        return render(request, 'csv_anonymizer/upload.html')

    def post(self, request):
        if not request.session.get("user_email"):
            return redirect('login_form')

        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            return render(request, 'csv_anonymizer/upload.html', {'error': 'Aucun fichier sélectionné'})

        if not csv_file.name.endswith('.csv'):
            return render(request, 'csv_anonymizer/upload.html', {'error': 'Le fichier doit être au format CSV'})

        csv_data = []
        csv_file_data = csv_file.read().decode('utf-8')
        reader = csv.reader(io.StringIO(csv_file_data))
        headers = next(reader)

        for row in reader:
            row_data = {}
            for i, header in enumerate(headers):
                row_data[header] = row[i]
            csv_data.append(row_data)

        user_email = request.session.get("user_email")  # Ajout facultatif si tu veux stocker l'auteur dans MongoDB
        print(request.session.get("user_email"))
        user = User.objects.filter(email=user_email).first()
        if not user:
    # Gérer le cas où l'utilisateur n'existe pas (par ex., erreur ou création)
             return render(request, 'csv_anonymizer/upload.html', {'error': "Utilisateur non trouvé."})

        job = AnonymizationJob.objects.create(
        user=user,
        original_filename=csv_file.name
        )

        collection.insert_one({
            'job_id': str(job.id),
            'headers': headers,
            'data': csv_data
        })

        analyzer = AnalyzerEngine()
        detected_entities = set()

        for row in csv_data[:10]:
            for header, value in row.items():
                if isinstance(value, str):
                    results = analyzer.analyze(text=value, language='fr')
                    for result in results:
                        detected_entities.add(result.entity_type)

        return render(request, 'csv_anonymizer/select_entities.html', {
            'job_id': job.id,
            'detected_entities': list(detected_entities),
            'headers': headers
        })
 
  
class ProcessCSVView( View):  
    def post(self, request, job_id):
        if not request.session.get("user_email"):
              return redirect('login_form')
  
        # Récupérer les entités sélectionnées  
        selected_entities = request.POST.getlist('entities')  
        selected_headers = request.POST.getlist('headers')  
          
        # Récupérer les données de MongoDB  
        job_data = collection.find_one({'job_id': str(job_id)})  
        if not job_data:  
            return JsonResponse({'error': 'Données non trouvées'}, status=404)  
          
        headers = job_data['headers']  
        csv_data = job_data['data']  
          
        # Convertir en DataFrame pandas  
        df = pd.DataFrame(csv_data)  
          
        # Filtrer pour ne traiter que les colonnes sélectionnées  
        df_to_process = df[selected_headers]  
          
        # Initialiser les moteurs Presidio Structured  
        pandas_engine = StructuredEngine()  
        pandas_analysis_builder = PandasAnalysisBuilder()  
          
        # Générer l'analyse pour les colonnes sélectionnées  
        structured_analysis = pandas_analysis_builder.generate_analysis(  
            df_to_process,  
            language="fr"  
        )  
          
        # Définir les opérateurs d'anonymisation  
        operators = {entity: OperatorConfig("replace", {"new_value": "[MASQUÉ]"})   
                    for entity in selected_entities}  
          
        # Anonymiser le DataFrame  
        anonymized_df = pandas_engine.anonymize(  
            data=df_to_process,  
            structured_analysis=structured_analysis,  
            operators=operators  
        )  
          
        # Remplacer les colonnes originales par les colonnes anonymisées  
        for header in selected_headers:  
            if header in anonymized_df.columns:  
                df[header] = anonymized_df[header]  
          
        # Mettre à jour le statut du job  
        job = AnonymizationJob.objects.get(id=job_id)  
        job.status = 'completed'  
        job.save()  
          
        # Préparer le fichier CSV à télécharger  
        output = io.StringIO()  
        df.to_csv(output, index=False)  
          
        # Créer la réponse HTTP avec le fichier CSV  
        response = HttpResponse(output.getvalue(), content_type='text/csv')  
        response['Content-Disposition'] = f'attachment; filename="anonymized_{job.original_filename}"'  
          
        # Nettoyer les données de MongoDB  
        collection.delete_one({'job_id': str(job_id)})  
          
        return response