import xmltodict
import json
import requests


def get_ibb_user_info(username):
    body = f"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://ws.ozlukbilgi.ik.ibb.gov.tr/">
               <soapenv:Header/>
               <soapenv:Body>
                  <ws:KisiSorgula>
                     <!--Optional:-->
                     <KisiBilgiInputType>
                        <logonAdi>{username}</logonAdi>
                        <servisKullaniciAdi>cbs</servisKullaniciAdi>
                     </KisiBilgiInputType>
                  </ws:KisiSorgula>
               </soapenv:Body>
            </soapenv:Envelope>
            """
    req = requests.post("https://api.ibb.gov.tr/IK/KisiBilgiOzlukService?wsdl", headers={'content-type': 'text/xml'},
                        data=body, verify=False)
    json_val = json.loads(json.dumps(xmltodict.parse(req.content)))
    infos = json_val.get("S:Envelope").get("S:Body").get("ns2:KisiSorgulaResponse").get("return").get("kisiBilgiList")
    return infos