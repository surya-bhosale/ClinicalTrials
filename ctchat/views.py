from django.shortcuts import render
import pandas as pd
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .serializers import *
import os
from rest_framework.generics import CreateAPIView, ListAPIView
from django.http import JsonResponse
import openai 
import json
from utils.preprocessing import ct_preprocessing
from utils.config import *


# Create your views here.
class ClinicalTrialsLLMView(CreateAPIView):
    # permission_classes = (IsAuthenticated,)
    # authentication_classes = (TokenAuthentication,)
    serializer_class = DorisChatSerializer
    
    df = None
    converted_list_to_dict = None
    
    @classmethod
    def get_df(cls, desired_keys):
        if cls.df is not None:
            return cls.df

        count = 0
        cls.df = pd.DataFrame()

        for file in os.listdir('/code/clinical_trials/breast_clinial_trials'):
            count += 1
            print('JSON LOADED: {}'.format(count))
            with open(f'/code/clinical_trials/breast_clinial_trials/{file}') as f:
                json_data = json.load(f)
            filtered_json_data = {key: json_data.get(key) for key in desired_keys}
            temp_df = pd.DataFrame([filtered_json_data])
            if len(temp_df['Locations'][0]) > 1:
                exp_location = temp_df.explode('Locations')
                cls.df = pd.concat([cls.df, exp_location])
            else:
                cls.df = pd.concat([cls.df, temp_df])
        return cls.df
    
    def convert_list_to_dicts(self, cell):
        if isinstance(cell, list):
            temp_dict = {}
            for d in cell:
                if isinstance(d, dict):
                    temp_dict.update(d)
            self.converted_list_to_dict = True
            return temp_dict
        return cell
    
    def strip_location(self, df):
        for col in df.columns:
            if 'Location' in col:
                new_col_name = col.replace('Location', '')
                df.rename(columns={col: new_col_name.strip()}, inplace=True)
        return df

    def normalize_cols(self, df):
        location_normalized = pd.json_normalize(df['Locations'])
        df = pd.concat([df.reset_index(drop=True), location_normalized.reset_index(drop=True)],axis=1)
        df.drop('Locations', axis=1, inplace=True)
        condition_normalized  = pd.json_normalize(df['Conditions'])
        condition_normalized['Condition'] = condition_normalized['Condition'].apply(lambda x : x[0])
        df = pd.concat([df, condition_normalized], axis=1);df.drop('Conditions', axis=1, inplace=True)
        return df
    
    @classmethod
    def make_df_if_csv_exists(cls, ct_type):
        if cls.df is not None:
            return cls.df

        count = 0
        cls.df = pd.DataFrame()
        with open('/code/ct_csv/trials.json') as ct_json:
            ct_json = json.load(ct_json)
        if os.path.exists(ct_json[ct_type]):
            cls.df = pd.read_csv(ct_json['Breast Cancer'])
            return cls.df
        else:
            raise Exception(f"CSV file for '{ct_type}' does not exist.")
    
            
    def post(self, request, *args, **kwargs):
        # user_id  = self.request.user.user_id
        # if not self.converted_list_to_dict:
        #     df['Locations'] = df['Locations'].apply(self.convert_list_to_dicts)
        # norm_cols_df = self.normalize_cols(df)
        # df = self.strip_location(norm_cols_df)
        df = self.make_df_if_csv_exists(ct_type='Breast Cancer')
        print(df)
        query = request.data.get('query', [])
        print(query)
        if query:
            openai.api_key = OPEN_API_KEY
            payload = df.ask(query, verbose=True)
            if payload.empty:
                json_payload = []
            else:
                json_payload = payload.to_json(orient='records')
                
            return JsonResponse({'Message':json_payload})
        else:
            return JsonResponse({'Message':{}})