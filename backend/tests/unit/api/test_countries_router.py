"""国家配置接口单元测试"""
import pytest
from fastapi.testclient import TestClient


class TestCountriesRouter:
    """国家配置接口测试"""

    def test_get_countries_list(self, client: TestClient):
        """测试获取国家列表"""
        response = client.get("/api/v1/countries")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "countries" in data["data"]
        assert isinstance(data["data"]["countries"], list)

        # 验证每个国家的结构
        countries = data["data"]["countries"]
        if countries:
            first_country = countries[0]
            assert "code" in first_country
            assert "name" in first_country
            assert "tax_type" in first_country

    def test_get_country_detail_success(self, client: TestClient):
        """测试获取存在的国家详情"""
        response = client.get("/api/v1/countries/TH")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data

        # 验证国家详情结构
        country = data["data"]
        assert "country_code" in country
        assert "country_name" in country
        assert "currency" in country
        assert "tax_rate" in country
        assert "registration_threshold" in country

    def test_get_country_detail_not_found(self, client: TestClient):
        """测试获取不存在的国家详情"""
        response = client.get("/api/v1/countries/XX")

        # 应该返回404
        assert response.status_code == 404

    def test_country_list_contains_thailand(self, client: TestClient):
        """测试国家列表包含泰国"""
        response = client.get("/api/v1/countries")

        assert response.status_code == 200
        data = response.json()
        countries = data["data"]["countries"]

        # 泰国应该在列表中
        thailand = next((c for c in countries if c["code"] == "TH"), None)
        assert thailand is not None
        assert "泰国" in thailand["name"] or "Thailand" in thailand["name"]

    def test_country_list_contains_vietnam(self, client: TestClient):
        """测试国家列表包含越南"""
        response = client.get("/api/v1/countries")

        assert response.status_code == 200
        data = response.json()
        countries = data["data"]["countries"]

        # 越南应该在列表中
        vietnam = next((c for c in countries if c["code"] == "VN"), None)
        assert vietnam is not None
        assert "越南" in vietnam["name"] or "Vietnam" in vietnam["name"]

    def test_thailand_tax_rate(self, client: TestClient):
        """测试泰国VAT税率配置"""
        response = client.get("/api/v1/countries/TH")

        assert response.status_code == 200
        data = response.json()
        country = data["data"]

        # 泰国标准VAT税率通常是7%
        assert country["tax_rate"] > 0
        assert country["tax_rate"] <= 100  # 合理范围

    def test_country_response_structure(self, client: TestClient):
        """验证国家接口响应结构"""
        response = client.get("/api/v1/countries/TH")

        assert response.status_code == 200
        data = response.json()

        # 验证外层结构
        assert "code" in data
        assert "msg" in data
        assert "data" in data

        # 验证data结构
        country = data["data"]
        assert "country_code" in country
        assert "country_name" in country
        assert "currency" in country
        assert "tax_rate" in country
        assert "registration_threshold" in country
        assert "business_types" in country
        assert "platforms" in country
