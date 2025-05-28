from uuid import uuid4

from axe_selenium_python import Axe
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from .accessibility_tester import AccessibilityTester
from .forms import URLForm, RegisterForm
from .models import Violation, WebsiteScan


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("url_check")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
def url_check_view(request):
    if request.method == "POST":
        form = URLForm(request.POST)
        if not form.is_valid():
            return render(request, "check_form.html", {"form": form})

        url = form.cleaned_data["url"]

        tester = AccessibilityTester(url)
        tester.start_driver()
        tester.test_page()

        axe = Axe(tester.driver)
        axe.inject()
        results = axe.run()

        screenshot = tester.driver.get_screenshot_as_png()

        tester.driver.quit()

        scan = WebsiteScan.objects.create(
            url=url,
            user=request.user,
            doc_language_ok=tester.correct["doc_language"],
            doc_language_errors=tester.wrong["doc_language"],
            alt_texts_ok=tester.correct["alt_texts"],
            alt_texts_errors=tester.wrong["alt_texts"],
            input_labels_ok=tester.correct["input_labels"],
            input_labels_errors=tester.wrong["input_labels"],
            empty_buttons_ok=tester.correct["empty_buttons"],
            empty_buttons_errors=tester.wrong["empty_buttons"],
            empty_links_ok=tester.correct["empty_links"],
            empty_links_errors=tester.wrong["empty_links"],
            color_contrast_ok=tester.correct["color_contrast"],
            color_contrast_errors=tester.wrong["color_contrast"],
        )
        scan.screenshot.save(f"{uuid4()}.png", ContentFile(screenshot), save=True)

        for v in results["violations"]:
            for node in v["nodes"]:
                Violation.objects.create(
                    scan=scan,
                    violation_id=v["id"],
                    impact=v.get("impact"),
                    description=v["description"],
                    help_text=v["help"],
                    help_url=v["helpUrl"],
                    failure_summary=node.get("failureSummary", ""),
                    html_snippet=node.get("html", "")
                )

        return redirect(f"{reverse('results')}?scan_id={scan.id}")
    else:
        form = URLForm()

    return render(request, "check_form.html", {"form": form})


@login_required
def results_view(request):
    scan_id = request.GET.get("scan_id")
    scan = WebsiteScan.objects.get(id=scan_id)
    violations = scan.violations.all()

    score = AccessibilityTester.calculate_result(
        {
            "doc_language": scan.doc_language_ok,
            "alt_texts": scan.alt_texts_ok,
            "input_labels": scan.input_labels_ok,
            "empty_buttons": scan.empty_buttons_ok,
            "empty_links": scan.empty_links_ok,
            "color_contrast": scan.color_contrast_ok,
        },
        {
            "doc_language": scan.doc_language_errors,
            "alt_texts": scan.alt_texts_errors,
            "input_labels": scan.input_labels_errors,
            "empty_buttons": scan.empty_buttons_errors,
            "empty_links": scan.empty_links_errors,
            "color_contrast": scan.color_contrast_errors,
        },
    )

    return render(request, "results.html", {
        "violations": violations,
        "scan": scan,
        "score": int(score * 100),
    })


@login_required
def my_scans_view(request):
    scans = WebsiteScan.objects.filter(user=request.user).order_by("-timestamp")
    return render(request, "my_scans.html", {"scans": scans})
