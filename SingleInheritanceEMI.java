// Parent class
class loan {
    double principal;
    double annualRate;
    int timeYears;

    loan(double principal, double annualRate, int timeYears) {
        this.principal = principal;
        this.annualRate = annualRate;
        this.timeYears = timeYears;
    }

    void displayLoanDetails() {
        System.out.println("Loan Amount: " + principal);
        System.out.println("Annual Interest Rate: " + annualRate + "%");
        System.out.println("Time Duration: " + timeYears + " years");
    }
}

// Child class extends Loan
class EMI extends loan {
    EMI(double principal, double annualRate, int timeYears) {
        super(principal, annualRate, timeYears);
    }

    void calculateEMI() {
        int months = timeYears * 12;
        double monthlyRate = (annualRate / 100) / 12;

        // EMI Formula
        double emi = (principal * monthlyRate * Math.pow(1 + monthlyRate, months)) /
                     (Math.pow(1 + monthlyRate, months) - 1);

        double totalPayment = emi * months;
        double interestAmount = totalPayment - principal;
        double interestPercent = (interestAmount / principal) * 100;

        System.out.println("\n--- EMI Calculation ---");
        System.out.printf("Monthly EMI: %.2f\n", emi);
        System.out.printf("Total Payment: %.2f\n", totalPayment);
        System.out.printf("Total Interest: %.2f\n", interestAmount);
        System.out.printf("Interest Percentage: %.2f%%\n", interestPercent);
    }
}

// Main class
public class SingleInheritanceEMI {
    public static void main(String[] args) {
        // Example: Principal = 3000000, Rate = 12%, Time = 5 years
        EMI loan = new EMI(100000, 10, 2);

        loan.displayLoanDetails();
        loan.calculateEMI();
    }
}
