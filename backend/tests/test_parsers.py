"""Test suite for multi-language code parsers and complexity calculations."""
from app.parsers.python_parser import PythonParser
from app.parsers.javascript_parser import JavaScriptParser
from app.parsers.typescript_parser import TypeScriptParser
from app.parsers.java_parser import JavaParser


def test_python_parser_functions_and_classes():
    code = '''
import os
from datetime import datetime

class Calculator:
    """A sample calculator class."""
    def add(self, a: int, b: int) -> int:
        return a + b

    def divide(self, a: int, b: int) -> float:
        if b == 0:
            raise ValueError("Division by zero")
        return a / b

def compute_total(items: list) -> float:
    total = 0.0
    for item in items:
        if item > 0:
            total += item
    return total
'''
    parser = PythonParser()
    res = parser.parse(code, "calc.py")

    assert res.language == "python"
    assert len(res.classes) == 1
    assert res.classes[0].name == "Calculator"
    assert len(res.classes[0].methods) == 2

    assert len(res.functions) == 1
    assert res.functions[0].name == "compute_total"
    assert res.functions[0].cyclomatic_complexity > 1

    assert len(res.imports) == 2
    assert res.errors == []


def test_javascript_parser_functions_and_classes():
    code = '''
import { useState } from 'react';
const axios = require('axios');

class DataService extends BaseService {
    fetchData() {
        return axios.get('/api/data');
    }
}

export const processList = (items) => {
    if (!items || items.length === 0) {
        return [];
    }
    return items.filter(x => x.active);
};
'''
    parser = JavaScriptParser()
    res = parser.parse(code, "service.js")

    assert res.language == "javascript"
    assert len(res.classes) == 1
    assert res.classes[0].name == "DataService"
    assert len(res.functions) >= 1
    assert len(res.imports) == 2


def test_typescript_parser_interfaces_and_types():
    code = '''
interface UserProfile {
    id: string;
    username: string;
}

enum Role {
    ADMIN,
    USER
}

export function getUser(id: string): UserProfile {
    return { id, username: "dev" };
}
'''
    parser = TypeScriptParser()
    res = parser.parse(code, "user.ts")

    assert res.language == "typescript"
    assert any("interface UserProfile" in c.name for c in res.classes)
    assert any("enum Role" in c.name for c in res.classes)
    assert len(res.functions) >= 1


def test_java_parser():
    code = '''
package com.codesage;

import java.util.List;
import java.util.ArrayList;

public class OrderService {
    public double calculateTotal(List<Double> prices) {
        double total = 0.0;
        for (Double price : prices) {
            if (price != null && price > 0) {
                total += price;
            }
        }
        return total;
    }
}
'''
    parser = JavaParser()
    res = parser.parse(code, "OrderService.java")

    assert res.language == "java"
    assert len(res.classes) == 1
    assert "OrderService" in res.classes[0].name
    assert len(res.functions) == 1
    assert res.functions[0].name == "calculateTotal"
    assert res.functions[0].cyclomatic_complexity >= 2
    assert len(res.imports) == 2
