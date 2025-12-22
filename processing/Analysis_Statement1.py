# cashflow_model.py

from config.Settings import TAX_RATE, RISK_FREE_RATE, BETA
from typing import List, Dict, Optional


class CashFlowModel:
    def __init__(
        self,
        #income_data_list: List[Dict],
        income_data: Optional[Dict] = None,
        balance_data: Optional[Dict] = None,  # งบ balance sheet
        #cashflow_data_list: List[Dict],
        cashflow_data: Optional[Dict] = None,
        #balance_data_list: List[Dict],
    ):
        self.income_data = income_data or {}
        self.balance_data = balance_data or {} # งบ Balance Sheet
        self.cashflow_data = cashflow_data or {}   # งบ Cash Flow Statement

    def cost_of_equity(self, market_return=None):
        if market_return is None:
            market_return = [0.07, 0.08, 0.09, 0.10]
        avg_market_return = sum(market_return) / len(market_return)
        return RISK_FREE_RATE + BETA * (avg_market_return - RISK_FREE_RATE)

    
    def interest_paid(self, cashflow_data):
        operations = {
            "Interest Paid": -1,
            "Interest Received": 1,
            "Debt Issued": 1,
            "Debt Repaid": -1,
        }
        value = 0
        for key, sign in operations.items():
            if key in cashflow_data:
                value += sign * cashflow_data[key]
        return value

    def wacc(self):
        #print(self.income_data_list)
        #print(self.cashflow_data_list)
        equity = self.balance_data.get("Total Equity") or self.balance_data.get("Total Shareholder Equity")  #.get 
        debt = self.balance_data.get("Total Debt")
        #sprint(self.balance_data)

        if not equity or (equity <= 0 and debt <= 0):
            raise ValueError("Total Equity and Total Debt ต้องมากกว่า 0 เพื่อคำนวณ WACC")

        interest_paid = self.balance_data.get("Interest Paid") or self.interest_paid(self.balance_data) #.get
        effective_cost_of_debt = interest_paid / debt if debt else 0
        after_tax_cost_of_debt = effective_cost_of_debt * (1 - TAX_RATE)

        total_capital = equity + debt
        weight_equity = equity / total_capital
        weight_debt = debt / total_capital

        return round((weight_equity * self.cost_of_equity()) + (weight_debt * after_tax_cost_of_debt), 2)

    def Operating_Cash_Flow(self):
        if self.income_data["Net Income"] == 0:
            raise ValueError("Net Income  ต้องมากกว่า 0")
        return self.income_data["Net Income"] + self.income_data["Depreciation and Amortization"] + self.cashflow_data["Stock Based Compensation"] + self.cashflow_data["Other Non Cash Items"] + self.cashflow_data["Change in Working Capital"]


    def Free_Cash_Flow(self):
        ocf =  self.Operating_Cash_Flow()
        if ocf == 0:
            raise ValueError("Operating Cash Flow เป็น 0")
        return ocf - self.cashflow_data["Capital Expenditure"]
    
    def unlevered_free_cash_flow(self):  # income_data, cashflow_data
        required_keys_income = {"Operating Income", "Depreciation and Amortization"}
        required_keys_cashflow = {"Capital Expenditure", "Change in Working Capital"}

        if not required_keys_income.issubset(self.income_data) or not required_keys_cashflow.issubset(self.cashflow_data):
            return None

        try:
            return (
                self.income_data["Operating Income"] * (1 - TAX_RATE)
                + self.income_data["Depreciation and Amortization"]
                - self.cashflow_data["Capital Expenditure"]
                - self.cashflow_data["Change in Working Capital"]
               # + income_data["Depreciation and Amortization"]
               # - cashflow_data["Capital Expenditure"]
               # - cashflow_data["Change in Working Capital"]
            )
        except:
            return None

    def growth_rate_cagr(self, start: float, end: float, years: int = 5):
        if start <= 0 or end <= 0:
            raise ValueError("FCF ต้องมากกว่า 0 เพื่อคำนวณ CAGR")
        return (end / start) ** (1 / years) - 1
    
    """def dcf_model_multiyear(self, years=10):
        if len(self.income_data) < years or len(self.cashflow_data) < years:
            raise ValueError("ข้อมูลไม่พอสำหรับ {} ปี".format(years))

        wacc = self.wacc()
        dcf_values = []

        last_valid_ufcf = None
        last_valid_year = 0

        for i in range(years):
            income = self.income_data[i]
            cashflow = self.cashflow_data[i]

            ufcf = self.unlevered_free_cash_flow(income, cashflow)
            if ufcf is None:
                dcf_values.append(None)
                continue

            discounted_cash_flow = ufcf / ((1 + wacc) ** (i + 1))
            dcf_values.append(round(discounted_cash_flow, 2))

            last_valid_ufcf = ufcf
            last_valid_year = i + 1

        if last_valid_ufcf is None:
            raise ValueError("ไม่มีข้อมูลเพียงพอในการคำนวณ Terminal Value")

        try:
            ufcf_start = self.unlevered_free_cash_flow(self.income_data[0], self.cashflow_data[0])
            ufcf_end = last_valid_ufcf
            growth = self.growth_rate_cagr(ufcf_start, ufcf_end, last_valid_year)
        except Exception:
            growth = 0.05

        terminal_value = (last_valid_ufcf * (1 + growth)) / (wacc - growth)
        terminal_discounted = terminal_value / ((1 + wacc) ** last_valid_year)
        dcf_values.append(round(terminal_discounted, 2))

        return dcf_values """

    def intrinsic_value_per_share(self):
        dcf_results = self.dcf_model_multiyear()
        total_dcf = sum(filter(None, dcf_results))
        shares = self.balance_data.get("Shares Outstanding", 1)  #.get
        if shares <= 0:
            raise ValueError("Shares Outstanding ต้องมากกว่า 0")
        return round(total_dcf / shares, 2)

# =============== Efficiency Ratios =================#

    def asset_turnover(self):
        "แสดงถึงประสิทธิภาพในการใช้สินทรัพย์เพื่อสร้างรายได้"
        revenue = self.income_data.get("Revenue")
        total_assets = self.balance_data.get("Total Assets")
        if revenue or not total_assets <= 0:
            raise ValueError("Revenue และ Total Assets ต้องมากกว่า 0 เพื่อคำนวณ Asset Turnover")
        return round(revenue / total_assets, 2)
    
    def inventory_turnover(self):
        "แสดงถึง ประสิทธิภาพในการจัดการสินค้าคงคลัง"
        cost_of_goods_sold = self.income_data.get("Cost of Goods Sold")
        inventory = self.balance_data.get("Inventory")
        if cost_of_goods_sold or None or  inventory <= 0:
            raise ValueError("Cost of Goods Sold และ Inventory ต้องมากกว่า 0 เพื่อคำนวณ Inventory Turnover")
        return round(cost_of_goods_sold / inventory, 2)
    
    def receivables_turnover(self):
        "แสดงถึงประสิทธิภาพในการจัดการลูกหนี้"
        revenue = self.income_data.get("Revenue")
        accounts_receivable = self.balance_data.get("Accounts Receivable")
        if revenue is None or accounts_receivable <= 0:
            raise ValueError("Revenue และ Accounts Receivable ต้องมากกว่า 0 เพื่อคำนวณ Receivables Turnover")
        return round(revenue / accounts_receivable, 2)
    
    def days_inventory_outstanding(self):
        "แสดงถึงจำนวนวันที่สินค้าคงคลังอยู่ในระบบ"
        inventory_turnover = self.inventory_turnover()
        if inventory_turnover is None:
            raise ValueError("ไม่สามารถคำนวณ Days Inventory Outstanding ได้ เนื่องจาก Inventory Turnover เป็น None")
        return round(365 / inventory_turnover, 2)
    
    def days_sales_outstanding(self):
        "แสดงถึงจำนวนวันที่ลูกหนี้ค้างชำระอยู่"
        receivables_turnover = self.receivables_turnover()
        if receivables_turnover is None:
            raise ValueError("ไม่สามารถคำนวณ Days Sales Outstanding ได้ เนื่องจาก Receivables Turnover เป็น None")
        return round(365 / receivables_turnover, 2)

    def working_capital_turnover(self):
        "แสดงถึงประสิทธิภาพในการใช้เงินทุนหมุนเวียน"
        revenue = self.income_data.get("Revenue")
        total_current_assets = self.balance_data.get("Total Current Assets")
        total_current_liabilities = self.balance_data.get("Total Current Liabilities")
        if revenue is not total_current_assets or not total_current_liabilities <= 0:
            raise ValueError("Revenue, Total Current Assets และ Total Current Liabilities ต้องมากกว่า 0 เพื่อคำนวณ Working Capital Turnover")
        return round(revenue / (total_current_assets - total_current_liabilities), 2)
    
# ================ Profitability Ratios =================#
    def ROE(self):
        if self.balance_data.get("Total Shareholder Equity") is None or self.income_data.get("Net Income") is None:
            raise ValueError("Total Shareholder Equity และ Net Income ต้องมีค่าเพื่อคำนวณ ROE")
        return round(self.income_data["Net Income"] / self.balance_data["Total Shareholder Equity"] * 100, 2)

    def ROA(self):
        if self.balance_data.get("Total Assets") is None or self.income_data.get("Net Income") is None:
            raise ValueError("Total Assets และ Net Income ต้องมีค่าเพื่อคำนวณ ROA")
        return round(self.income_data["Net Income"] / self.balance_data["Total Assets"] * 100, 2)

    def gross_profit_margin(self):
        if self.income_data.get("Gross Profit") is None or self.income_data.get("Revenue") is None:
            raise ValueError("Gross Profit และ Revenue ต้องมีค่าเพื่อคำนวณ Gross Profit Margin")
        return round(self.income_data["Gross Profit"] / self.income_data["Revenue"] * 100, 2)
    
    def operation_profit_margin(self):
        if self.income_data.get("Operating Income") == 0:
            raise ValueError("Operating Income ต้องมีค่าเพื่อคำนวณ Operating Profit Margin")
        return round(self.income_data["Operating Income"] / self.income_data["Revenue"] * 100, 2)
    
    def net_profit_margin(self):
        if self.income_data.get("Net Income") == 0:
            raise ValueError("Net Income ต้องมีค่าเพื่อคำนวณ Net Profit Margin")
        return round(self.income_data["Net Income"] / self.income_data["Revenue"] * 100, 2)
    
    def ebitda_margin(self):
        if self.income_data.get("EBITDA") == 0:
            raise ValueError("EBITDA ต้องมีค่าเพื่อคำนวณ EBITDA Margin")
        return round(self.income_data["EBITDA"] / self.income_data["Revenue"] * 100, 2)

# ================ Valuation ======================#

    def Owners_Earnings(self):
        net_income = self.income_data.get("Net Income")
        depreation = self.cashflow_data.get("Depreciation and Amortization")
        capital_expenditure = self.cashflow_data.get("Capital Expenditure")
        change_in_working_capital = self.cashflow_data.get("Change in Working Capital")
        if net_income is None or depreation is None or capital_expenditure is None or change_in_working_capital is None:
            raise ValueError("ข้อมูลไม่เพียงพอในการคำนวณ Owner Earnings")
        return  net_income + depreation - capital_expenditure - change_in_working_capital

    def EPS_Ratio(self) -> float:
        net_income = self.income_data.get("Net Income")
        #shares_outstanding = self.balance_data.get("Shares Outstanding", 1)
        weighted_average_shares = self.income_data.get("Weighted Average Shares")
        if net_income is None or weighted_average_shares <=0:
            raise ValueError("Net Income และ Shares Oustanding ต้องมากกว่า 0 เพื่อคำนวณ EPS")
        return round(net_income / weighted_average_shares, 2)

    def PE_Ratio(self):
        """ คำนวณ P/E Ratio """
        price = self.income_data.get("price")
        eps = self.income_data.get("EPS")
        if price <= 0 or eps is None or eps <= 0:
            raise ValueError("Price และ EPS ต้องมากกว่า 0 เพื่อคำนวณ P/E Ratio")
        return round(price / eps, 2)

    

# ต้องแก้ใข
    def PB_Ratio(self):
        price = self.income_data.get("price")
        total_share_equity = self.balance_data.get("Total Shareholder Equity")
        shares_outstanding = self.balance_data.get("Shares Outstanding ") 
        
        print(total_share_equity, shares_outstanding, price)
        if not total_share_equity or not shares_outstanding or not price <= 0:
            raise ValueError("Total Shareholder Equity และ Common Stock ต้องมากกว่า 0 เพื่อคำนวณ PB Ratio")
        
        book_value = total_share_equity / shares_outstanding


        return price / book_value

# ================ Liquidity Ratios ==================#
    
    def current_ratio(self) -> float:
        if self.balance_data.get("Total Current Assets") <= 0:
            raise ValueError("Total Current Assets ต้องมากกว่า 0 เพื่อคำนวณ Current Ratio")
        return round(self.balance_data["Total Current Assets"] / self.balance_data["Total Current Liabilities"] * 100, 2)
    
    def quick_ratio(self) -> float:
        if self.balance_data.get("Total Current Assets") or self.balance_data["Inventory"] <= 0:
            raise ValueError("Total Current Assets และ Inventory ต้องมากกว่า 0 เพื่อคำนวณ Quick Ratio")
        return round((self.balance_data["Total Current Assets"] - self.balance_data["Inventory"] * 100, 2))

    def cash_ratio(self) -> float:
        if self.balance_data.get("Total Current Liabilities") is None == 0:
            raise ValueError("Cash and Cash Equivalents และ Short Term Investments ต้องมากกว่า 0 เพื่อคำนวณ Cash Ratio")
        return (self.balance_data["Cash and Cash Equivalents"] + self.balance_data["Short Term Investments"]) / self.balance_data["Total Current Liabilities"]
    
    
    