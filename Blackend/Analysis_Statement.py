import numpy as np
from Blackend.Settings import TAX_RATE, RISK_FREE_RATE, BETA
from typing import Dict, Optional


class CashFlowModel:
    def __init__(
        self,
        income_data: Optional[Dict] = None,
        balance_data: Optional[Dict] = None,
        cashflow_data: Optional[Dict] = None,
    ):
        self.income = income_data or {}
        self.balance = balance_data or {}
        self.cashflow = cashflow_data or {}

    # ================= Cost of Capital ================= #

    def cost_of_equity(self, market_return=None) -> float:
        market_return = np.array(market_return or [0.07, 0.08, 0.09, 0.10])
        return RISK_FREE_RATE + BETA * (market_return.mean() - RISK_FREE_RATE)

    def interest_paid(self) -> float:
        ops = {
            "Interest Paid": -1,
            "Interest Received": 1,
            "Debt Issued": 1,
            "Debt Repaid": -1,
        }
        return sum(sign * self.cashflow.get(k, 0) for k, sign in ops.items())

    def wacc(self) -> float:
        equity = self.balance.get("Total Shareholder Equity", 0)
        debt = self.balance.get("Total Debt", 0)

        if equity <= 0 and debt <= 0:
            raise ValueError("Equity หรือ Debt ต้องมากกว่า 0")

        interest = self.interest_paid()
        cost_debt = (interest / debt) if debt > 0 else 0
        cost_debt_after_tax = cost_debt * (1 - TAX_RATE)

        total = equity + debt
        wacc = (
            (equity / total) * self.cost_of_equity()
            + (debt / total) * cost_debt_after_tax
        )
        return round(wacc, 4)

    # ================= Cash Flow ================= #

    def Operating_Cash_Flow(self) -> float:
        return (
            self.income["Net Income"]
            + self.income["Depreciation and Amortization"]
            + self.cashflow.get("Stock Based Compensation", 0)
            + self.cashflow.get("Other Non Cash Items", 0)
            + self.cashflow["Change in Working Capital"]
        )

    def Free_Cash_Flow(self) -> float:
        return self.Operating_Cash_Flow() - self.cashflow["Capital Expenditure"]

    def unlevered_free_cash_flow(self) -> float:
        return (
            self.income["Operating Income"] * (1 - TAX_RATE)
            + self.income["Depreciation and Amortization"]
            - self.cashflow["Capital Expenditure"]
            - self.cashflow["Change in Working Capital"]
        )

    # ================= Growth ================= #

    #def growth_rate_cagr(self, start: float, end: float, years: int) -> float:
    #    return np.power(end / start, 1 / years) - 1

    # ================= DCF (Vectorized) ================= #

    #def dcf_model_multiyear(self, ufcf_series, years=10) -> np.ndarray:
    #    ufcf = np.array(ufcf_series[:years], dtype=float)

    #    if len(ufcf) < years:
    #       raise ValueError("ข้อมูล UFCF ไม่ครบ")

    #    wacc = self.wacc()
    #    t = np.arange(1, years + 1)
    #    discount_factor = np.power(1 + wacc, t)

    #    discounted = ufcf / discount_factor

        # Terminal Value
    #    g = self.growth_rate_cagr(ufcf[0], ufcf[-1], years)
    #    terminal = (ufcf[-1] * (1 + g)) / (wacc - g)
    #    terminal_discounted = terminal / np.power(1 + wacc, years)

    #    return np.append(discounted, terminal_discounted)

    #def intrinsic_value_per_share(self, ufcf_series) -> float:
    #    dcf = self.dcf_model_multiyear(ufcf_series)
    #    shares = self.income.get("Weighted Average Shares", 1)
    #    return round(dcf.sum() / shares, 2)

    def growth_rate_cagr(self, start: float, end: float, years: int) -> float:
        """
        CAGR แบบกันพัง:
        - ถ้าข้อมูลไม่เหมาะสม คืน 0.0 แทน (เพื่อไม่ให้ DCF ล่มทั้งระบบ)
        """
        try:
            if years <= 0:
                return 0.0
            if start is None or end is None:
                return 0.0

            start = float(start)
            end = float(end)

            # CAGR ไม่มีความหมายเมื่อ <=0 (ในบริบท DCF)
            if start <= 0 or end <= 0:
                return 0.0

            return float((end / start) ** (1.0 / years) - 1.0)
        except Exception:
            return 0.0

    # ================= DCF (Vectorized) ================= #

    def dcf_model_multiyear(self, ufcf_series, years: int = 10) -> np.ndarray:
        """
        คืน array: [PV(UFCF ปี1..ปีN), PV(Terminal)]
        """
        # แปลงเป็น array อย่างปลอดภัย
        ufcf = np.array(list(ufcf_series)[:years], dtype=float)

        if ufcf.size < years:
            raise ValueError("ข้อมูล UFCF ไม่ครบ")

        wacc = float(self.wacc() or 0.0)
        if wacc <= -0.99:
            raise ValueError("WACC ผิดปกติ (<= -99%)")

        # Discount UFCF
        t = np.arange(1, years + 1, dtype=float)
        discounted = ufcf / np.power(1.0 + wacc, t)

        # Terminal Value
        # ปีนับ CAGR: จาก ufcf[0] ไป ufcf[-1] มี (years-1) ช่วง
        g = self.growth_rate_cagr(ufcf[0], ufcf[-1], max(years - 1, 1))

        # กัน terminal ระเบิด: clamp g ให้น้อยกว่า wacc เสมอ
        # ปรับ margin ตามสไตล์คุณได้ (เช่น 0.005 = 0.5%)
        margin = 0.005
        if g >= wacc - margin:
            g = max(wacc - margin, -0.50)  # กันสุดโต่ง ไม่ให้ g ต่ำเวอร์

        terminal = (ufcf[-1] * (1.0 + g)) / (wacc - g)
        terminal_discounted = terminal / np.power(1.0 + wacc, years)

        return np.append(discounted, terminal_discounted)

    def intrinsic_value_per_share(self, ufcf_series, years: int = 10) -> float:
        """
        ราคาเหมาะสมต่อหุ้น = (PV(UFCF) + PV(Terminal)) / Shares
        """
        dcf_stream = self.dcf_model_multiyear(ufcf_series, years=years)
        total_value = float(np.sum(dcf_stream))

        # ดึง shares แบบปลอดภัย + รองรับ key หลายแบบ
        shares = (
            self.income.get("Weighted Average Shares")
            or self.income.get("Weighted Average Shares Outstanding")
            or self.income.get("WeightedAverageSharesOutstanding")
            or 1
        )

        try:
            shares = float(shares)
        except Exception:
            shares = 1.0

        if shares <= 0:
            shares = 1.0

        return round(total_value / shares, 2)
    
    # ================= Efficiency ================= #

    def asset_turnover(self) -> float:
        return self.income["Revenue"] / self.balance["Total Assets"]

    def inventory_turnover(self) -> float:
        return self.income["Cost of Goods Sold"] / self.balance["Inventory"]

    def receivables_turnover(self) -> float:
        return self.income["Revenue"] / self.balance["Accounts Receivable"]

    def days_inventory_outstanding(self) -> float:
        return 365 / self.inventory_turnover()

    def days_sales_outstanding(self) -> float:
        return 365 / self.receivables_turnover()

    def working_capital_turnover(self) -> float:
        wc = self.balance["Total Current Assets"] - self.balance["Total Current Liabilities"]
        return self.income["Revenue"] / wc

    # ================= Profitability ================= #

    # สูตร NOPAT สำหรับ ROIC
    def NOPAT(self) -> float:
        return self.income["EBITDA"] * (1 - TAX_RATE)

    def ROE(self) -> float:
        return (self.income["Net Income"] / self.balance["Total Shareholder Equity"]) * 100

    def ROA(self) -> float:
        return (self.income["Net Income"] / self.balance["Total Assets"]) * 100

    def ROIC(self) -> float: 
        invested_capital = (
            self.balance["Total Debt"] 
            + self.balance["Total Shareholder Equity"]
            - self.balance["Cash and Cash Equivalents"]
        )
        return (self.NOPAT() / invested_capital) * 100
    
    def gross_profit_margin(self) -> float:
        return (self.income["Gross Profit"] / self.income["Revenue"]) * 100

    def operation_profit_margin(self) -> float:
        return (self.income["Operating Income"] / self.income["Revenue"]) * 100

    def net_profit_margin(self) -> float:
        return (self.income["Net Income"] / self.income["Revenue"]) * 100

    def ebitda_margin(self) -> float:
        return (self.income["EBITDA"] / self.income["Revenue"]) * 100

    # ================= Valuation ================= #

    def Owners_Earnings(self) -> float:
        return (
            self.income["Net Income"]
            + self.cashflow["Depreciation and Amortization"]
            - self.cashflow["Capital Expenditure"]
            - self.cashflow["Change in Working Capital"]
        )

    def EPS_Ratio(self) -> float:
        return self.income["Net Income"] / self.income["Weighted Average Shares"]

    def PE_Ratio(self) -> float:
        return self.income["price"] / self.income["EPS"]

    def PBV_Ratio(self) -> float:
        """ 
         weighted_average_shares ใช้นี้แทน Shares Outstanding
        """
        total_shareholder_equity = float(self.balance["Total Shareholder Equity"])
        weighted_average_shares = float(self.income["Weighted Average Shares"])
        price = float(self.income["price"])
        #if total_shareholder_equity <= 0 or weighted_average_shares <= 0 or price <= 0:
        #    return 0.0
        
        book_value = total_shareholder_equity / weighted_average_shares
        return price / book_value

    # ================= Liquidity ================= #

    def current_ratio(self) -> float:
        return self.balance["Total Current Assets"] / self.balance["Total Current Liabilities"]

    def quick_ratio(self) -> float:
        return (
            (self.balance["Total Current Assets"] - self.balance["Inventory"])
            / self.balance["Total Current Liabilities"]
        )

    def cash_ratio(self) -> float:
        return (
            self.balance["Cash and Cash Equivalents"]
            + self.balance["Short Term Investments"]
        ) / self.balance["Total Current Liabilities"]
