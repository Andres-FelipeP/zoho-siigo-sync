from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
import os
from dotenv import load_dotenv
import json
import math
from datetime import datetime

app = Flask(__name__)
load_dotenv()


def current_user_zoho(access_token):
      header_user_current = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json"
      }
      user_current_url = "https://www.zohoapis.com/crm/v2/users?type=CurrentUser"
      whitelist_str = os.getenv('WHITE_LIST_ZOHO', '')
      whitelist = [email.strip() for email in whitelist_str.split(',')]

      try:
            response = requests.get(user_current_url, headers=header_user_current)
            response.raise_for_status()
            data = response.json()
            
            if 'users' in data and len(data['users']) > 0:
                  user = data['users'][0]
                  user_id = user.get('id')
                  user_email = user.get('email')
                  
                  print(f"User ID: {user_id}")
                  print(f"User Email: {user_email}")
                  
                  if user_email in whitelist:
                        print(f"User {user_email} is in the whitelist. Access granted.")
                        return True
                  else:
                        print(f"User {user_email} is NOT in the whitelist. Access denied.")
                        return False, f"Usuario {user_email} no autorizado para realizar esta operación"
            else:
                  return False, "No se pudo obtener información del usuario de Zoho"
                  
      except requests.exceptions.RequestException as e:
            return False, f"Error en la conexión con Zoho API: {str(e)}"
      except json.JSONDecodeError as e:
            return False, f"Error al procesar respuesta de Zoho: {str(e)}"
      except Exception as e:
            return False, f"Error validando usuario de Zoho: {str(e)}"

      

def auth_zoho(codigo):
      # Paso 1: Obtener access token con el código
      token_url_zoho = os.getenv("TOKEN_URL_ZOHO")
      client_id_zoho = os.getenv("CLIENT_ID_ZOHO")
      client_secret_zoho = os.getenv("CLIENT_SECRET_ZOHO")
      redirect_uri_zoho = os.getenv("REDIRECT_URI_ZOHO")
      
      params_zoho = {
            "code": codigo,
            "grant_type": "authorization_code",
            "scope": "ZohoCRM.modules.ALL,ZohoCRM.settings.ALL",
            "client_id": client_id_zoho,
            "client_secret": client_secret_zoho,
            "redirect_uri": redirect_uri_zoho,
            
      }
      
      token_response = requests.post(token_url_zoho, params=params_zoho)
      print(f"Token response url: {token_response.url}")
      print(f"Token response: {token_response}")

      token_json = token_response.json()
      
      
      if "access_token" not in token_json:
            print("Error al obtener tokens:", token_json)
            exit()
            
      access_token = token_json["access_token"]
      if not access_token:
            return jsonify({"error": "No se pudo obtener token de Zoho"}), 400
      return access_token

def auth_settings_variables_siigo():
      #! URL de autenticación de Siigo
      auth_url_siigo = os.getenv("AUTH_URL_SIIGO")

      # Datos para la autenticación
      auth_payload_siigo = {
            "username": os.getenv("SIIGO_USERNAME"),
            "access_key": os.getenv("SIIGO_ACCESS_KEY")
      }
      auth_response_siigo = requests.post(auth_url_siigo, json=auth_payload_siigo)
      auth_response_siigo.raise_for_status()
      auth_data_siigo = auth_response_siigo.json()
      access_token_siigo = auth_data_siigo.get('access_token')
      print("Access Token:", access_token_siigo)
      print("Autenticación exitosa siigo")
      
      siigo_partner = os.getenv("SIIGO_PARTNER")
      
      return access_token_siigo, siigo_partner

def obtener_contactos_zoho(zoho_url, headers_zoho):
      all_contacts = []
      page = 1
      per_page = 200
      print("Obteniendo contactos de Zoho...")
      
      try:
            while True:
                  params = {"page": page, "per_page": per_page}
                  
                  response = requests.get(zoho_url, headers=headers_zoho, params=params)
                  response.raise_for_status()  # Lanza excepciones para códigos de error HTTP
                  try:
                        data = response.json()
                        if "data" not in data or not data["data"]:
                              print("No se encontraron contactos en la respuesta de la API")
                              break
                        
                        all_contacts.extend(data["data"])
                        
                        if len(data["data"]) < per_page:
                              break
                        
                        page += 1
                        
                  except json.JSONDecodeError:
                        # print("Error al decodificar la respuesta JSON")
                        break
      
      except requests.exceptions.RequestException as e:
            print(zoho_url)
            print(headers_zoho)
            print(params)
            print(f"Error al conectar con la API de Zoho: {e}")
      
      print(f"Total contactos obtenidos: {len(all_contacts)}")
      return all_contacts

def siigo_contacts_number(from_date_data, headers_siigo):
      # Obtener el número total de clientes
      try:
            print('Iniciando solicitud a la API de Siigo...')
            print(f"Fecha de inicio: {from_date_data}")
            clients_response_1_siigo = requests.get(f"https://api.siigo.com/v1/customers?created_start={from_date_data}&page=1&page_size=1", headers=headers_siigo, timeout=30)
            print(clients_response_1_siigo)
            print('Solicitud completada')
      except requests.exceptions.Timeout:
            print("La solicitud a la API de Siigo ha excedido el tiempo de espera (timeout)")
      except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud a la API de Siigo: {e}")
            
            
      clients_1_siigo = clients_response_1_siigo.json()

      clients_number_siigo = clients_1_siigo.get('pagination', []).get('total_results', 0)
      
      # calular las paginas para obtener todos los clientes de a 100
      print(f"Total de resultados: {clients_number_siigo}")

      result_pages_siigo = math.ceil(clients_number_siigo/100)
      
      print(f"Total de páginas: {result_pages_siigo}")
      
      return clients_number_siigo, result_pages_siigo

def indexar_por_siigo_id(contactos_zoho):
      return {obj.get("SiigoID"): obj for obj in contactos_zoho}

def get_siigo_data(client):
      first_name = client["contacts"][0]["first_name"][:40]

      last_name = client["contacts"][0]["last_name"][:80]

      full_name = ""
      if last_name == "":
            full_name = first_name
      else:
            full_name = f"{first_name} {last_name}"
            
      tranformed_data = {}
      
      tranformed_data["First_Name"] = first_name
      
      tranformed_data["Last_Name"] = last_name if last_name else first_name
      
      tranformed_data["Email"] = client["contacts"][0]["email"]
      
      tranformed_data["Title"] = full_name[:100]
      
      tranformed_data['Indicativo_telefono'] = client["contacts"][0]["phone"]["indicative"]
      
      main_contact = client["contacts"][0]["phone"]["number"]
      
      tranformed_data["Phone"] = main_contact
      
      tranformed_data["Home_Phone"] = main_contact
      tranformed_data["Other_Phone"] = main_contact
      tranformed_data["Mobile"] = main_contact
      tranformed_data["Asst_Phone"] = main_contact
      tranformed_data["Full_Name"] = full_name
      
      tranformed_data["Mailing_Street"] = client["address"]["address"]
      tranformed_data["Mailing_City"] = client["address"]["city"]["city_name"]
      tranformed_data["Mailing_State"] = client["address"]["city"]["state_name"]
      tranformed_data["Mailing_Zip"] = client["address"]["city"]["city_code"]
      tranformed_data["Mailing_Country"] = client["address"]["city"]["country_name"]
      tranformed_data["Description"] = full_name
      tranformed_data["Tipo_Identificacion"] = client["id_type"]["name"][:100]
      tranformed_data["Tipo_Usuario"] = client["type"][:100] # Tpo usuario
      tranformed_data["Identificacion"] = client["identification"][:100]
      tranformed_data["Tipo_Persona"] = client["person_type"]
      tranformed_data["SiigoID"] = client["id"]
      tranformed_data["Nombre_Empresa"] = full_name[:255]
      tranformed_data["Estado"] = str(client["active"])[:100]
      
      
      return tranformed_data

def data_zoho_format(siigo_client_data):
      data = {
            "data": [{
                  "First_Name": siigo_client_data["First_Name"],
                  "Last_Name": siigo_client_data["Last_Name"],
                  "Email": siigo_client_data["Email"],
                  "Title": siigo_client_data["Title"],
                  "Indicativo_telefono": siigo_client_data["Indicativo_telefono"],
                  "Phone": siigo_client_data["Phone"],
                  "Home_Phone": siigo_client_data["Home_Phone"],
                  "Other_Phone": siigo_client_data["Other_Phone"],
                  "Mobile": siigo_client_data["Mobile"],
                  "Asst_Phone": siigo_client_data["Asst_Phone"],
                  "Full_Name": siigo_client_data["Full_Name"],
                  "Mailing_Street": siigo_client_data["Mailing_Street"],
                  "Mailing_City": siigo_client_data["Mailing_City"],
                  "Mailing_State": siigo_client_data["Mailing_State"],
                  "Mailing_Zip": siigo_client_data["Mailing_Zip"],
                  "Mailing_Country": siigo_client_data["Mailing_Country"],
                  
                  "Description": siigo_client_data["Description"],
                  "Tipo_Identificacion": siigo_client_data["Tipo_Identificacion"],
                  "Tipo_Usuario": siigo_client_data["Tipo_Usuario"], # Tipo usuario
                  "Identificacion": siigo_client_data["Identificacion"],
                  "Tipo_Persona": siigo_client_data["Tipo_Persona"],
                  "SiigoID": siigo_client_data["SiigoID"],
                  "Nombre_Empresa": siigo_client_data["Nombre_Empresa"],
                  "Estado": siigo_client_data["Estado"],
            }]
      }
      
      return data

def encontrar_siigo_id_en_zoho(siigo_id, contactos_zoho):
      # retorn objeto Tipo contacto de Zoho o None
      return contactos_zoho.get(siigo_id)



@app.route('/sync', methods=['POST'])
def sync():
      try:
            # Obtener datos de Power Automate Forms office 365
            data = request.json
            fecha = data.get('fechaSincronizacion')
            codigo = data.get('codigoZoho')
            correo = data.get('correoNotificacion')
            
            if not fecha or not codigo:
                  return jsonify({"error": "Faltan datos"}), 400

            # Paso 1: Autenticacion a la API de ZOHO
            try:
                  print(f'codigoooo: {codigo}')
                  access_token_zoho = auth_zoho(codigo)
                  
                  user_validation = current_user_zoho(access_token_zoho)
                  if user_validation != True:
                        # Si no es True, entonces es una tupla (False, error_message)
                        if isinstance(user_validation, tuple):
                              return jsonify({"error": user_validation[1]}), 403
                        else:
                              return jsonify({"error": "Error de validación de usuario"}), 403
                  
                  
                  print(f'Acces token: {access_token_zoho}')
                  zoho_url = os.getenv("CONTACTS_URL_ZOHO")
                  headers_zoho = {
                  "Authorization": f"Zoho-oauthtoken {access_token_zoho}",
                  "Content-Type": "application/json"
                  }
            except Exception as e:
                  return jsonify({"error": f"Error en la autenticación de Zoho: {str(e)}"}), 500
                  
            # Paso 2: Autenticacion a la API de Siigo
            try:
                  access_token_siigo, siigo_partner = auth_settings_variables_siigo()
                  headers_siigo = {
                  "Authorization": access_token_siigo,
                  "Partner-Id": siigo_partner,
                  "Content-Type": "application/json"
                  }
            except Exception as e:
                  return jsonify({"error": f"Error en la autenticación de Siigo: {str(e)}"}), 500
            
            try:
                  clients_number_siigo, result_pages_siigo = siigo_contacts_number(fecha, headers_siigo)
                  counter_clientes = 0
                  zoho_contacts = obtener_contactos_zoho(zoho_url, headers_zoho)
                  indexed_zoho_contacts_by_siigo_id = indexar_por_siigo_id(zoho_contacts)
            except Exception as e:
                  return jsonify({"error": f"Error obteniendo datos iniciales: {str(e)}"}), 500

            #! Obtener todos los clientes de Siigo
            logs_zoho_integration = 'Zoho Integration Logs:\n'
            try:
                  for n_page in range(1, result_pages_siigo+1):
                        clients_response_all_page = requests.get(f"https://api.siigo.com/v1/customers?created_start={fecha}&page={n_page}&page_size=100", headers=headers_siigo)
                        if clients_response_all_page.status_code != 200:
                              return jsonify({"error": f"Error obteniendo clientes de Siigo. Status: {clients_response_all_page.status_code}"}), 500
                              
                        clients_response_all_page_parsed = clients_response_all_page.json()
                  
                        # estos son los clientes de la pagina
                        clients_response_result = clients_response_all_page_parsed.get('results', [])
                        
                        for client in clients_response_result:
                              
                              if counter_clientes == clients_number_siigo:
                                    break
                              counter_clientes += 1
                              
                              try:
                                    siigo_client_data = get_siigo_data(client)
                                    data_transformed = data_zoho_format(siigo_client_data)
                                    
                                    if not zoho_contacts:
                                          # No hay contactos en Zoho, crear nuevo
                                          res = requests.post(zoho_url, headers=headers_zoho, json=data_transformed)
                                    else:
                                          # Hay contactos en Zoho, verificar si este ya existe
                                          object_founded = encontrar_siigo_id_en_zoho(client["id"], indexed_zoho_contacts_by_siigo_id)
                                          
                                          if object_founded:
                                                # El contacto ya existe en Zoho, actualizarlo
                                                res = requests.put(f"{zoho_url}/{object_founded['id']}", headers=headers_zoho, json=data_transformed)
                                          else:
                                                # El contacto no existe en Zoho, crearlo
                                                res = requests.post(zoho_url, headers=headers_zoho, json=data_transformed)
                                    
                                    # Verificar si la respuesta fue exitosa
                                    if res.status_code >= 400:
                                          error_msg = f"Error al sincronizar cliente {client.get('id')}: {res.status_code} {res.text}"
                                          logs_zoho_integration += f"{error_msg}\n"
                                          print(error_msg)
                                    else:
                                          logs_zoho_integration += f"{res.status_code} {res.json()}\n"
                                          
                                          
                              except Exception as e:
                                    error_msg = f"Error procesando cliente {client.get('id')}: {str(e)}"
                                    logs_zoho_integration += f"{error_msg}\n"
                                    print(error_msg)
                                    continue
            except Exception as e:
                  return jsonify({"error": f"Error durante la sincronización: {str(e)}"}), 500
            return jsonify({"success": "Datos sincronizados"}), 200
      except Exception as e:
            return jsonify({"error": f"Error general en la sincronización: {str(e)}"}), 500

@app.route('/code')
def mostrar_codigo():
      code = request.args.get('code')
      return render_template('codigo.html', code=code)

# Ruta para logo u otros recursos
@app.route('/static/<path:filename>')
def static_files(filename):
      return send_from_directory(app.static_folder, filename)

# Ruta para que el cronjob haga ping
@app.route('/ping')
def ping():
      current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      return jsonify({"message": "Ping successful", "timestamp": current_time})

@app.route('/leads')
def leads():
      return render_template('leads.html')

@app.route('/casos')
def casos():
      return render_template('casos.html')

@app.route('/proveedores')
def proveedores():
      return render_template('proveedores.html')

@app.route('/')
def home():
      return render_template('base.html')

@app.route('/exito')
def exito():
      return render_template('gracias.html')

if __name__ == '__main__':
      app.run(debug=True)