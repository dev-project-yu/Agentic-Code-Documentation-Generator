from __future__ import annotations

from typing import Dict, List

from app.models import OntologyEntity, OntologyRelationship


class OntologyBuilder:
    @staticmethod
    def from_analysis(repo_analysis: Dict) -> Dict:
        entities: List[OntologyEntity] = []
        relationships: List[OntologyRelationship] = []

        repo_id = repo_analysis["repo"]["full_name"].replace("/", "__")
        entities.append(
            OntologyEntity(
                entity_id=repo_id,
                type="Repository",
                name=repo_analysis["repo"]["full_name"],
                source_path=".",
                source_file="README.md",
                properties={"default_branch": repo_analysis["repo"].get("default_branch", "main")},
            )
        )

        for file in repo_analysis.get("files", []):
            file_id = f"{repo_id}:{file['path']}"
            entities.append(
                OntologyEntity(
                    entity_id=file_id,
                    type="File",
                    name=file["path"],
                    source_path=file["path"],
                    source_file=file["path"],
                    properties={"extension": file.get("extension", "")},
                )
            )
            relationships.append(OntologyRelationship(repo_id, file_id, "contains"))

        for module in repo_analysis.get("modules", []):
            module_id = f"{repo_id}:{module['name']}"
            entities.append(
                OntologyEntity(
                    entity_id=module_id,
                    type="Module",
                    name=module["name"],
                    source_path=module.get("path", ""),
                    source_file=module.get("path", ""),
                    properties={"language": module.get("language", "python")},
                )
            )
            relationships.append(OntologyRelationship(repo_id, module_id, "owns"))

        for cls in repo_analysis.get("classes", []):
            class_id = f"{repo_id}:{cls['name']}"
            entities.append(
                OntologyEntity(
                    entity_id=class_id,
                    type="Class",
                    name=cls["name"],
                    source_path=cls.get("path", ""),
                    source_file=cls.get("path", ""),
                    line_number=cls.get("line_number"),
                    properties={"module": cls.get("module")},
                )
            )
            relationships.append(OntologyRelationship(class_id, cls.get("module_id", repo_id), "belongs_to"))

        for func in repo_analysis.get("functions", []):
            func_id = f"{repo_id}:{func['name']}"
            entities.append(
                OntologyEntity(
                    entity_id=func_id,
                    type="Function",
                    name=func["name"],
                    source_path=func.get("path", ""),
                    source_file=func.get("path", ""),
                    line_number=func.get("line_number"),
                    properties={"module": func.get("module")},
                )
            )
            relationships.append(OntologyRelationship(func_id, func.get("module_id", repo_id), "belongs_to"))

        for api in repo_analysis.get("api_endpoints", []):
            api_id = f"{repo_id}:{api['path']}:{api['method']}"
            entities.append(
                OntologyEntity(
                    entity_id=api_id,
                    type="API",
                    name=f"{api['method']} {api['path']}",
                    source_path=api.get("path", ""),
                    source_file=api.get("source_file", ""),
                    line_number=api.get("line_number"),
                    properties={"method": api.get("method"), "handler": api.get("handler")},
                )
            )
            relationships.append(OntologyRelationship(api_id, api.get("module_id", repo_id), "implemented_in"))

        for dependency in repo_analysis.get("dependencies", []):
            dep_id = f"{repo_id}:{dependency['name']}"
            entities.append(
                OntologyEntity(
                    entity_id=dep_id,
                    type="Dependency",
                    name=dependency["name"],
                    source_path="requirements.txt",
                    source_file="requirements.txt",
                    properties={"version": dependency.get("version")},
                )
            )
            relationships.append(OntologyRelationship(repo_id, dep_id, "depends_on"))

        return {"entities": [e.__dict__ for e in entities], "relationships": [r.__dict__ for r in relationships]}
