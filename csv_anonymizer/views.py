from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views import View
from pymongo import MongoClient
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import pandas as pd
from presidio_structured import StructuredEngine, PandasAnalysisBuilder
import csv
import io
import json
from .models import AnonymizationJob

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
        # Vérifiez l'authentification
        user_email = request.session.get("user_email")
        if not user_email:
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

        # Utiliser l'email de l'utilisateur stocké en session
        job = AnonymizationJob.objects.create(
            user_email=user_email,  # Utiliser l'email au lieu de l'objet User
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
                    results = analyzer.analyze(text=value, language='en')
                    for result in results:
                        detected_entities.add(result.entity_type)

        return render(request, 'csv_anonymizer/select_entities.html', {
            'job_id': job.id,
            'detected_entities': list(detected_entities),
            'headers': headers
        })


class ProcessCSVView(View):
    def post(self, request, job_id):
        # Vérifiez l'authentification
        if not request.session.get("user_email"):
            return redirect('login_form')
            
        # Récupérer les entités sélectionnées (types de données à masquer)
        selected_entities = request.POST.getlist('entities')
        
        # Récupérer les données de MongoDB
        job_data = collection.find_one({'job_id': str(job_id)})
        if not job_data:
            return JsonResponse({'error': 'Données non trouvées'}, status=404)
        
        headers = job_data['headers']
        csv_data = job_data['data']
        
        # Convertir en DataFrame pandas
        df = pd.DataFrame(csv_data)
        
        # Initialiser les moteurs Presidio Structured
        pandas_engine = StructuredEngine()
        pandas_analysis_builder = PandasAnalysisBuilder()
        
        # Générer l'analyse pour TOUTES les colonnes
        # Presidio va automatiquement identifier les colonnes contenant des données sensibles
        structured_analysis = pandas_analysis_builder.generate_analysis(
            df,
            language="en"
        )
        
        # Filtrer l'analyse pour ne garder que les entités sélectionnées par l'utilisateur
        filtered_analysis = {}
        for column_name, column_analysis in structured_analysis.items():
            filtered_column_analysis = []
            for entity_analysis in column_analysis:
                if entity_analysis.entity_type in selected_entities:
                    filtered_column_analysis.append(entity_analysis)
            if filtered_column_analysis:
                filtered_analysis[column_name] = filtered_column_analysis
        
        # Définir les opérateurs d'anonymisation pour les entités sélectionnées
        operators = {entity: OperatorConfig("replace", {"new_value": "[MASQUÉ]"})
                    for entity in selected_entities}
        
        # Anonymiser uniquement les colonnes qui contiennent effectivement les entités sélectionnées
        if filtered_analysis:
            anonymized_df = pandas_engine.anonymize(
                data=df,
                structured_analysis=filtered_analysis,
                operators=operators
            )
            
            # Remplacer les valeurs originales par les valeurs anonymisées
            # Uniquement pour les colonnes qui ont effectivement été anonymisées
            for column in anonymized_df.columns:
                if column in df.columns:
                    df[column] = anonymized_df[column]
        
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
    
    
    
class ProcessCSVView(View):
    def post(self, request, job_id):
        # Vérifiez l'authentification
        if not request.session.get("user_email"):
            return redirect('login_form')
            
        # Récupérer les entités sélectionnées
        selected_entities = request.POST.getlist('entities')
        # Ces headers ne sont plus utilisés pour filtrer, mais juste pour avoir la liste complète
        selected_headers = request.POST.getlist('headers') if 'headers' in request.POST else []
        
        # Récupérer les données de MongoDB
        job_data = collection.find_one({'job_id': str(job_id)})
        if not job_data:
            return JsonResponse({'error': 'Données non trouvées'}, status=404)
        
        headers = job_data['headers']
        csv_data = job_data['data']
        
        # Convertir en DataFrame pandas
        df = pd.DataFrame(csv_data)
        
        # Initialiser les moteurs Presidio
        analyzer = AnalyzerEngine()
        anonymizer = AnonymizerEngine()
        
        # Créer une copie du DataFrame pour la sortie
        output_df = df.copy()
        
        # Pour chaque colonne du DataFrame
        for column in df.columns:
            # Pour chaque ligne dans cette colonne
            for index, value in df[column].items():
                # Vérifier si la valeur est une chaîne avant de l'analyser
                if isinstance(value, str):
                    # Analyser pour détecter les entités
                    results = analyzer.analyze(text=value, language='en')
                    
                    # Filtrer les résultats pour ne garder que les entités sélectionnées
                    results = [r for r in results if r.entity_type in selected_entities]
                    
                    # Si des entités à anonymiser ont été trouvées
                    if results:
                        # Configurer l'anonymisation pour remplacer les valeurs
                        anonymizers = {entity_type: OperatorConfig("replace", {"new_value": "[MASQUÉ]"})
                                      for entity_type in selected_entities}
                        
                        # Anonymiser le texte
                        anonymized_text = anonymizer.anonymize(
                            text=value,
                            analyzer_results=results,
                            operators=anonymizers
                        ).text
                        
                        # Remplacer la valeur dans le DataFrame de sortie
                        output_df.at[index, column] = anonymized_text
        
        # Mettre à jour le statut du job
        job = AnonymizationJob.objects.get(id=job_id)
        job.status = 'completed'
        job.save()
        
        # Préparer le fichier CSV à télécharger
        output = io.StringIO()
        output_df.to_csv(output, index=False)
        
        # Créer la réponse HTTP avec le fichier CSV
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="anonymized_{job.original_filename}"'
        
        # Nettoyer les données de MongoDB
        collection.delete_one({'job_id': str(job_id)})
        
        return response