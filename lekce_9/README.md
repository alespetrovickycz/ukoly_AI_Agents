# AI agent, ktery analyzuje Wazuh incidenty ulozene v OpenSearch a vytvori report incidentu za poslednich 7 dni a navrhne reseni na snizeni poctu incidentu

  - navrhni mi vlastni MCP server v pythonu a integruj do nej tool pro vyhledavani informaci o incidentech v OpenSearch
  - navrhni agenta, ktery bude pouzivat tento MCP server (remote HTTP) a jeho tools
  - agent bude komunikovat s lokalni ollamou pres litellm proxy s modelem llama3
  - jako agent framework pouzij langchain
  - analyzuje incidenty za poslednich 7 dni a vytvori PDF dokument s prehledem a sumarizaci incidentu
  - navrhne reseni na snizeni poctu incidentu
  - OpenSearch pristupove udaje budou v .env, nazvy navrhni
  - indexy v opensearch maji pattern s datumem napr. wazuh-alerts-4.x-2025.11.28
  - v reportu me zajima lokalita zdroje incidentu (region_name), typ incidentu (groups), zavaznost incidentu (rule.level), statistika dle jednotlivych serveru (agent.name), statistika podle pouziteho dekoderu (decoder.name)
  - agent use an LLM to generate intelligent recommendations based on patterns
  - sepis mi instrukce jak spustit a nastavit litellm v dockeru a spojit ji s ollamou s llama3 modelem
  - plan muze nacist az 1000 incidentu k detailni analyze, tento limit at je konfigurovatelny
  - doporuceni at obsahuje strategicke i takticke doporuceni
  - mam k dispozici funkcni opensearch instanci s wazuh incidenty


## Report
  - obecny prehled - celkovy pocet incidentu, podle levelu, podle typu (groups)
  - report v cestine
  - Timeline/trend chart
  - Top 10 most frequent incidents
  - Recommendations section
  - vcetne vizualizaci a grafu
  - jako logo firmy na report pouzij logo-full-color-cropped.png


## incident dokument v opensearch vypada napriklad takto:

{
  "_index": "wazuh-alerts-4.x-2025.11.28",
  "_id": "Bf2DypoB6rQ6Dr_WyhnA",
  "_version": 1,
  "_score": null,
  "_source": {
    "input": {
      "type": "log"
    },
    "agent": {
      "ip": "1.2.3.4",
      "name": "host.example.com",
      "id": "3686"
    },
    "manager": {
      "name": "manager.example.com"
    },
    "data": {
      "protocol": "GET",
      "srcip": "80.188.48.227",
      "id": "404",
      "url": "/wpad.dat"
    },
    "rule": {
      "firedtimes": 1282,
      "mail": false,
      "level": 5,
      "pci_dss": [
        "6.5",
        "11.4"
      ],
      "tsc": [
        "CC6.6",
        "CC7.1",
        "CC8.1",
        "CC6.1",
        "CC6.8",
        "CC7.2",
        "CC7.3"
      ],
      "description": "Web server 400 error code.",
      "groups": [
        "web",
        "accesslog",
        "attack"
      ],
      "id": "31101",
      "nist_800_53": [
        "SA.11",
        "SI.4"
      ],
      "gdpr": [
        "IV_35.7.d"
      ]
    },
    "location": "/var/log/nginx/access.log",
    "decoder": {
      "name": "web-accesslog"
    },
    "id": "1764334224.22560884",
    "GeoLocation": {
      "city_name": "Prague",
      "country_name": "Czechia",
      "region_name": "Hlavni mesto Praha",
      "location": {
        "lon": 14.5148,
        "lat": 50.0766
      }
    },
    "full_log": "80.188.48.227 - - [28/Nov/2025:13:50:23 +0100] \"GET /wpad.dat HTTP/1.1\" 404 416 127 0.000 - \"-\" \"WinHttp-Autoproxy-Service/5.1\"",
    "timestamp": "2025-11-28T13:50:24.147+0100"
  },
  "fields": {
    "timestamp": [
      "2025-11-28T12:50:24.147Z"
    ]
  },
  "sort": [
    1764334224147
  ]
}

## kompletni opensearch mapping

{
  "properties": {
    "cluster": {
      "type": "object",
      "properties": {
        "name": {
          "type": "keyword"
        }
      }
    },
    "configSum": {
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      },
      "type": "text"
    },
    "dateAdd": {
      "type": "date"
    },
    "disconnection_time": {
      "type": "date"
    },
    "group": {
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      },
      "type": "text"
    },
    "group_config_status": {
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      },
      "type": "text"
    },
    "host": {
      "type": "keyword"
    },
    "id": {
      "type": "keyword"
    },
    "ip": {
      "type": "keyword"
    },
    "lastKeepAlive": {
      "type": "date"
    },
    "manager": {
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      },
      "type": "text"
    },
    "mergedSum": {
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      },
      "type": "text"
    },
    "name": {
      "type": "keyword"
    },
    "node_name": {
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      },
      "type": "text"
    },
    "os": {
      "type": "object",
      "properties": {
        "arch": {
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "type": "text"
        },
        "codename": {
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "type": "text"
        },
        "major": {
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "type": "text"
        },
        "minor": {
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "type": "text"
        },
        "name": {
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "type": "text"
        },
        "platform": {
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "type": "text"
        },
        "uname": {
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "type": "text"
        },
        "version": {
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "type": "text"
        }
      }
    },
    "registerIP": {
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      },
      "type": "text"
    },
    "status": {
      "type": "keyword"
    },
    "status_code": {
      "type": "long"
    },
    "timestamp": {
      "format": "dateOptionalTime",
      "type": "date"
    },
    "version": {
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      },
      "type": "text"
    }
  }
}
